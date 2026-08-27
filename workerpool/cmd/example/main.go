// Command example demonstrates workerpool with graceful shutdown on
// SIGINT/SIGTERM: in-flight jobs are allowed to finish, new submissions are
// rejected, and shutdown is forced after a timeout if jobs don't cooperate.
package main

import (
	"context"
	"errors"
	"fmt"
	"log"
	"math/rand"
	"os/signal"
	"syscall"
	"time"

	"github.com/euintelhub-lang/wkb/workerpool"
)

func main() {
	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	pool := workerpool.New(ctx, 4, workerpool.WithQueueSize(16), workerpool.WithErrorBuffer(16))

	go func() {
		for err := range pool.Errors() {
			log.Printf("job error: %v", err)
		}
	}()

	go produce(ctx, pool)

	<-ctx.Done()
	log.Println("shutdown signal received, draining in-flight jobs...")

	shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	if err := pool.Shutdown(shutdownCtx); err != nil {
		log.Printf("graceful shutdown timed out, forcing stop: %v", err)
		pool.Stop()
	}

	log.Println("all workers exited cleanly")
}

// produce keeps submitting jobs until ctx is cancelled or the pool stops
// accepting new work.
func produce(ctx context.Context, pool *workerpool.Pool) {
	for i := 1; ; i++ {
		id := i
		err := pool.Submit(ctx, func(ctx context.Context) error {
			return runJob(ctx, id)
		})
		if err != nil {
			if !errors.Is(err, context.Canceled) && !errors.Is(err, workerpool.ErrPoolClosed) {
				log.Printf("submit failed: %v", err)
			}
			return
		}
	}
}

// runJob simulates a unit of work that respects cancellation.
func runJob(ctx context.Context, id int) error {
	work := time.Duration(200+rand.Intn(300)) * time.Millisecond
	select {
	case <-time.After(work):
		fmt.Printf("job %d done (%s)\n", id, work)
		return nil
	case <-ctx.Done():
		return fmt.Errorf("job %d interrupted: %w", id, ctx.Err())
	}
}
