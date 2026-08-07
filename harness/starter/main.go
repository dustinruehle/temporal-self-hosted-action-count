package main

import (
	"context"
	"flag"
	"fmt"
	"log"
	"sync"
	"time"

	"github.com/google/uuid"
	"go.temporal.io/sdk/client"

	"github.com/temporal-sa/action-count-harness/moneytransfer"
	"github.com/temporal-sa/action-count-harness/orderfulfillment"
)

func main() {
	transfers := flag.Int("transfers", 50, "number of money-transfer workflows to run")
	orders := flag.Int("orders", 25, "number of order-fulfillment workflows to run")
	spread := flag.Float64("spread", 60, "seconds to spread the starts over, so rate()/APS is measurable (0 = fire all at once)")
	flag.Parse()

	c, err := client.Dial(client.Options{HostPort: "localhost:7233"})
	if err != nil {
		log.Fatalln("unable to create client:", err)
	}
	defer c.Close()
	ctx := context.Background()

	// Pace starts across `spread` seconds. A single burst makes rate()/APS read ~0
	// (nothing rises across a scrape window); sustained load gives a real APS curve.
	var pace time.Duration
	if total := *transfers + *orders; *spread > 0 && total > 0 {
		pace = time.Duration(float64(time.Second) * *spread / float64(total))
	}

	var wg sync.WaitGroup
	var sampleTransferID, sampleOrderID, sampleChildID string

	// --- Money transfers ---
	for i := 0; i < *transfers; i++ {
		id := fmt.Sprintf("money-transfer-%d-%s", i, uuid.NewString()[:8])
		if i == 0 {
			sampleTransferID = id
		}
		run, err := c.ExecuteWorkflow(ctx, client.StartWorkflowOptions{
			ID:        id,
			TaskQueue: moneytransfer.TaskQueue,
		}, moneytransfer.MoneyTransfer, moneytransfer.TransferDetails{
			Amount: 54.99, FromAccount: "001-001", ToAccount: "002-002", ReferenceID: uuid.NewString(),
		})
		if err != nil {
			log.Fatalln("start transfer:", err)
		}
		wg.Add(1)
		go func(r client.WorkflowRun) { defer wg.Done(); _ = r.Get(ctx, nil) }(run)
		time.Sleep(pace)
	}

	// --- Orders (each spawns a ReserveInventory child; each gets one Query) ---
	for i := 0; i < *orders; i++ {
		id := fmt.Sprintf("order-%d-%s", i, uuid.NewString()[:8])
		if i == 0 {
			sampleOrderID = id
			sampleChildID = "reserve-inventory-" + id
		}
		run, err := c.ExecuteWorkflow(ctx, client.StartWorkflowOptions{
			ID:        id,
			TaskQueue: orderfulfillment.TaskQueue,
		}, orderfulfillment.OrderFulfillment, orderfulfillment.Order{
			OrderID: id, Items: []string{"widget", "gadget"}, Amount: 129.99,
		})
		if err != nil {
			log.Fatalln("start order:", err)
		}
		wfID := run.GetID()
		wg.Add(1)
		go func(r client.WorkflowRun, wfID string) {
			defer wg.Done()
			_ = r.Get(ctx, nil)
			// One Query per order: billable, but never recorded in Event History.
			if _, err := c.QueryWorkflow(ctx, wfID, "", "status"); err != nil {
				log.Printf("query %s failed: %v", wfID, err)
			}
		}(run, wfID)
		time.Sleep(pace)
	}

	wg.Wait()
	log.Printf("Completed %d money transfers and %d orders (+%d children, +%d queries)",
		*transfers, *orders, *orders, *orders)
	fmt.Println("---SAMPLE-IDS-FOR-PATH-B---")
	fmt.Printf("MoneyTransfer=%s\n", sampleTransferID)
	fmt.Printf("OrderFulfillment=%s\n", sampleOrderID)
	fmt.Printf("ReserveInventory=%s\n", sampleChildID)
}
