package moneytransfer

import (
	"context"
	"fmt"
	"time"

	"go.temporal.io/sdk/temporal"
	"go.temporal.io/sdk/workflow"
)

const TaskQueue = "action-count-tq"

type TransferDetails struct {
	Amount      float64
	FromAccount string
	ToAccount   string
	ReferenceID string
}

// MoneyTransfer is a saga-style transfer: withdraw then deposit, with
// compensation registered for the withdraw if a later step fails. On the
// success path it produces a small, hand-countable set of billable Actions:
//
//	WorkflowExecutionStarted (1) + Withdraw activity (1) + Deposit activity (1) = 3
func MoneyTransfer(ctx workflow.Context, d TransferDetails) error {
	ao := workflow.ActivityOptions{
		StartToCloseTimeout: time.Minute,
		RetryPolicy:         &temporal.RetryPolicy{MaximumAttempts: 3},
	}
	ctx = workflow.WithActivityOptions(ctx, ao)

	var compensations []func()
	var err error
	defer func() {
		if err != nil {
			// Run compensations in reverse order (saga rollback).
			for i := len(compensations) - 1; i >= 0; i-- {
				compensations[i]()
			}
		}
	}()

	if err = workflow.ExecuteActivity(ctx, Withdraw, d).Get(ctx, nil); err != nil {
		return err
	}
	compensations = append(compensations, func() {
		_ = workflow.ExecuteActivity(ctx, WithdrawCompensation, d).Get(ctx, nil)
	})

	if err = workflow.ExecuteActivity(ctx, Deposit, d).Get(ctx, nil); err != nil {
		return err
	}
	return nil
}

func Withdraw(_ context.Context, d TransferDetails) error {
	fmt.Printf("Withdrawing $%.2f from %s (ref %s)\n", d.Amount, d.FromAccount, d.ReferenceID)
	return nil
}

func WithdrawCompensation(_ context.Context, d TransferDetails) error {
	fmt.Printf("Compensating withdraw $%.2f to %s (ref %s)\n", d.Amount, d.FromAccount, d.ReferenceID)
	return nil
}

func Deposit(_ context.Context, d TransferDetails) error {
	fmt.Printf("Depositing $%.2f into %s (ref %s)\n", d.Amount, d.ToAccount, d.ReferenceID)
	return nil
}
