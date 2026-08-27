package workerpool

import (
	"context"
	"errors"
	"sync/atomic"
	"testing"
	"time"
)

func TestPoolRunsAllTasks(t *testing.T) {
	ctx := context.Background()
	p := New(ctx, 4)

	const n = 50
	var completed int64
	for i := 0; i < n; i++ {
		if err := p.Submit(ctx, func(ctx context.Context) error {
			atomic.AddInt64(&completed, 1)
			return nil
		}); err != nil {
			t.Fatalf("Submit: %v", err)
		}
	}

	if err := p.Shutdown(context.Background()); err != nil {
		t.Fatalf("Shutdown: %v", err)
	}

	if got := atomic.LoadInt64(&completed); got != n {
		t.Fatalf("completed = %d, want %d", got, n)
	}
}

func TestShutdownWaitsForInFlightTasks(t *testing.T) {
	ctx := context.Background()
	p := New(ctx, 2)

	started := make(chan struct{})
	release := make(chan struct{})
	var finished int64

	if err := p.Submit(ctx, func(ctx context.Context) error {
		close(started)
		<-release
		atomic.AddInt64(&finished, 1)
		return nil
	}); err != nil {
		t.Fatalf("Submit: %v", err)
	}

	<-started

	shutdownDone := make(chan error, 1)
	go func() {
		shutdownDone <- p.Shutdown(context.Background())
	}()

	select {
	case <-shutdownDone:
		t.Fatal("Shutdown returned before in-flight task finished")
	case <-time.After(50 * time.Millisecond):
	}

	close(release)

	if err := <-shutdownDone; err != nil {
		t.Fatalf("Shutdown: %v", err)
	}
	if atomic.LoadInt64(&finished) != 1 {
		t.Fatal("task did not run to completion before Shutdown returned")
	}
}

func TestSubmitAfterShutdownFails(t *testing.T) {
	ctx := context.Background()
	p := New(ctx, 1)

	if err := p.Shutdown(context.Background()); err != nil {
		t.Fatalf("Shutdown: %v", err)
	}

	if err := p.Submit(ctx, func(ctx context.Context) error { return nil }); !errors.Is(err, ErrPoolClosed) {
		t.Fatalf("Submit after Shutdown = %v, want ErrPoolClosed", err)
	}
}

func TestShutdownDeadlineCancelsInFlightTasks(t *testing.T) {
	ctx := context.Background()
	p := New(ctx, 1)

	cancelled := make(chan struct{})
	if err := p.Submit(ctx, func(ctx context.Context) error {
		<-ctx.Done()
		close(cancelled)
		return ctx.Err()
	}); err != nil {
		t.Fatalf("Submit: %v", err)
	}

	shutdownCtx, cancel := context.WithTimeout(context.Background(), 20*time.Millisecond)
	defer cancel()

	if err := p.Shutdown(shutdownCtx); !errors.Is(err, context.DeadlineExceeded) {
		t.Fatalf("Shutdown = %v, want DeadlineExceeded", err)
	}

	select {
	case <-cancelled:
	case <-time.After(time.Second):
		t.Fatal("in-flight task was never cancelled after Shutdown deadline")
	}
}

func TestStopDiscardsQueuedTasks(t *testing.T) {
	ctx := context.Background()
	p := New(ctx, 1, WithQueueSize(10))

	// Occupy the single worker with a task that blocks until the pool's
	// context is cancelled, so the 5 tasks below are guaranteed to still be
	// sitting in the queue (never started) when Stop is called.
	started := make(chan struct{})
	if err := p.Submit(ctx, func(ctx context.Context) error {
		close(started)
		<-ctx.Done()
		return ctx.Err()
	}); err != nil {
		t.Fatalf("Submit: %v", err)
	}
	<-started

	var queued int64
	for i := 0; i < 5; i++ {
		if err := p.Submit(ctx, func(ctx context.Context) error {
			atomic.AddInt64(&queued, 1)
			return nil
		}); err != nil {
			t.Fatalf("Submit: %v", err)
		}
	}

	p.Stop()

	if got := atomic.LoadInt64(&queued); got != 0 {
		t.Fatalf("queued tasks run after Stop = %d, want 0 (Stop should discard them)", got)
	}
}

func TestErrorsChannelDeliversAndCloses(t *testing.T) {
	ctx := context.Background()
	p := New(ctx, 2, WithErrorBuffer(4))

	boom := errors.New("boom")
	if err := p.Submit(ctx, func(ctx context.Context) error { return boom }); err != nil {
		t.Fatalf("Submit: %v", err)
	}
	if err := p.Submit(ctx, func(ctx context.Context) error { return nil }); err != nil {
		t.Fatalf("Submit: %v", err)
	}

	if err := p.Shutdown(context.Background()); err != nil {
		t.Fatalf("Shutdown: %v", err)
	}

	var got []error
	for err := range p.Errors() {
		got = append(got, err)
	}

	if len(got) != 1 || !errors.Is(got[0], boom) {
		t.Fatalf("Errors() = %v, want [boom]", got)
	}
}

func TestNewPanicsOnInvalidWorkerCount(t *testing.T) {
	defer func() {
		if recover() == nil {
			t.Fatal("New(ctx, 0) did not panic")
		}
	}()
	New(context.Background(), 0)
}
