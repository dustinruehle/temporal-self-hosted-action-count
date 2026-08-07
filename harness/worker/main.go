package main

import (
	"log"

	"go.temporal.io/sdk/client"
	"go.temporal.io/sdk/worker"

	"github.com/temporal-sa/action-count-harness/moneytransfer"
	"github.com/temporal-sa/action-count-harness/orderfulfillment"
)

func main() {
	c, err := client.Dial(client.Options{HostPort: "localhost:7233"})
	if err != nil {
		log.Fatalln("unable to create client:", err)
	}
	defer c.Close()

	w := worker.New(c, "action-count-tq", worker.Options{})

	// Money transfer
	w.RegisterWorkflow(moneytransfer.MoneyTransfer)
	w.RegisterActivity(moneytransfer.Withdraw)
	w.RegisterActivity(moneytransfer.WithdrawCompensation)
	w.RegisterActivity(moneytransfer.Deposit)

	// Order fulfillment (parent + child)
	w.RegisterWorkflow(orderfulfillment.OrderFulfillment)
	w.RegisterWorkflow(orderfulfillment.ReserveInventory)
	w.RegisterActivity(orderfulfillment.ValidateOrder)
	w.RegisterActivity(orderfulfillment.ChargePayment)
	w.RegisterActivity(orderfulfillment.SendConfirmation)
	w.RegisterActivity(orderfulfillment.CheckStock)
	w.RegisterActivity(orderfulfillment.ReserveItems)

	log.Println("worker started on task queue action-count-tq")
	if err := w.Run(worker.InterruptCh()); err != nil {
		log.Fatalln("worker stopped:", err)
	}
}
