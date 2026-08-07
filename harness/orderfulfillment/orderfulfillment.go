package orderfulfillment

import (
	"context"
	"fmt"
	"time"

	"go.temporal.io/sdk/temporal"
	"go.temporal.io/sdk/workflow"
)

const TaskQueue = "action-count-tq"

type Order struct {
	OrderID string
	Items   []string
	Amount  float64
}

// OrderFulfillment is an order-management parent Workflow that exercises every
// billable Action shape the recipe's counter claims to handle:
//
//	WorkflowExecutionStarted        1
//	ValidateOrder activity          1
//	ReserveInventory child workflow 2  (children are billed at 2x)
//	ChargePayment local activity    1  (local activities collapse to 1)
//	Timer (shipping delay)          1
//	SendConfirmation activity       1
//	                              ----
//	parent-history billable total   7
//
// The ReserveInventory child runs as its own Execution with its own history
// (start + 2 activities = 3), so a from-history estimate must count it as a
// separate Workflow Type. A per-execution Query is issued by the starter; it
// is billable but never lands in Event History.
func OrderFulfillment(ctx workflow.Context, o Order) (string, error) {
	status := "received"
	if err := workflow.SetQueryHandler(ctx, "status", func() (string, error) {
		return status, nil
	}); err != nil {
		return "", err
	}

	ao := workflow.ActivityOptions{
		StartToCloseTimeout: time.Minute,
		RetryPolicy:         &temporal.RetryPolicy{MaximumAttempts: 3},
	}
	ctx = workflow.WithActivityOptions(ctx, ao)

	if err := workflow.ExecuteActivity(ctx, ValidateOrder, o).Get(ctx, nil); err != nil {
		return "", err
	}
	status = "validated"

	cwo := workflow.ChildWorkflowOptions{WorkflowID: "reserve-inventory-" + o.OrderID}
	cctx := workflow.WithChildOptions(ctx, cwo)
	var reservation string
	if err := workflow.ExecuteChildWorkflow(cctx, ReserveInventory, o).Get(cctx, &reservation); err != nil {
		return "", err
	}
	status = "reserved"

	lao := workflow.LocalActivityOptions{StartToCloseTimeout: time.Minute}
	lctx := workflow.WithLocalActivityOptions(ctx, lao)
	var confirmation string
	if err := workflow.ExecuteLocalActivity(lctx, ChargePayment, o).Get(lctx, &confirmation); err != nil {
		return "", err
	}
	status = "charged"

	// Shipping delay -> a durable Timer (billable). Kept short so runs finish fast.
	_ = workflow.Sleep(ctx, time.Second)

	if err := workflow.ExecuteActivity(ctx, SendConfirmation, o).Get(ctx, nil); err != nil {
		return "", err
	}
	status = "completed"
	return "order " + o.OrderID + " fulfilled", nil
}

// ReserveInventory is the child Workflow: start + 2 activities = 3 Actions.
func ReserveInventory(ctx workflow.Context, o Order) (string, error) {
	ao := workflow.ActivityOptions{StartToCloseTimeout: time.Minute}
	ctx = workflow.WithActivityOptions(ctx, ao)

	if err := workflow.ExecuteActivity(ctx, CheckStock, o).Get(ctx, nil); err != nil {
		return "", err
	}
	if err := workflow.ExecuteActivity(ctx, ReserveItems, o).Get(ctx, nil); err != nil {
		return "", err
	}
	return "reserved:" + o.OrderID, nil
}

func ValidateOrder(_ context.Context, o Order) error {
	fmt.Printf("Validating order %s (%d items)\n", o.OrderID, len(o.Items))
	return nil
}

func ChargePayment(_ context.Context, o Order) (string, error) {
	fmt.Printf("Charging $%.2f for order %s\n", o.Amount, o.OrderID)
	return "charge-ok-" + o.OrderID, nil
}

func SendConfirmation(_ context.Context, o Order) error {
	fmt.Printf("Sending confirmation for order %s\n", o.OrderID)
	return nil
}

func CheckStock(_ context.Context, o Order) error {
	fmt.Printf("Checking stock for order %s\n", o.OrderID)
	return nil
}

func ReserveItems(_ context.Context, o Order) error {
	fmt.Printf("Reserving items for order %s\n", o.OrderID)
	return nil
}
