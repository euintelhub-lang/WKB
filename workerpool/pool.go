// Package workerpool implements a fixed-size pool of goroutines that execute
// submitted tasks concurrently and can be shut down gracefully.
package workerpool

import (
	"context"
	"errors"
	"sync"
)

// Task is a unit of work submitted to the pool. It receives the pool's
// context and returns an error, which is delivered on the pool's error
// channel (see Errors) if the send isn't cut short by shutdown.
type Task func(ctx context.Context) error

// ErrPoolClosed is returned by Submit once the pool is no longer accepting
// new tasks (Shutdown or Stop has been called).
var ErrPoolClosed = errors.New("workerpool: pool is closed")

// Pool is a fixed-size pool of worker goroutines that pull tasks off a
// shared queue and run them concurrently.
type Pool struct {
	tasks  chan Task
	errs   chan error
	wg     sync.WaitGroup
	ctx    context.Context
	cancel context.CancelFunc

	closeOnce sync.Once
	closed    chan struct{}
}

// Option configures a Pool at construction time.
type Option func(*config)

type config struct {
	queueSize int
	errBuf    int
}

// WithQueueSize sets the capacity of the pending-task queue. The default is
// 0 (unbuffered — Submit blocks until a worker picks up the task).
func WithQueueSize(n int) Option {
	return func(c *config) { c.queueSize = n }
}

// WithErrorBuffer sets the buffer size of the channel returned by Errors.
// The default is 0. Once the buffer fills, workers block delivering errors
// until the caller drains Errors, so size it to how fast that happens.
func WithErrorBuffer(n int) Option {
	return func(c *config) { c.errBuf = n }
}

// New creates a Pool with n worker goroutines and starts them immediately.
// n must be at least 1. ctx bounds the whole pool's lifetime: if it is
// cancelled, the pool behaves as if Stop had been called. Callers must
// eventually call Shutdown or Stop to release the pool's goroutines and
// close the Errors channel.
func New(ctx context.Context, n int, opts ...Option) *Pool {
	if n < 1 {
		panic("workerpool: n must be >= 1")
	}

	var cfg config
	for _, opt := range opts {
		opt(&cfg)
	}

	ctx, cancel := context.WithCancel(ctx)

	p := &Pool{
		tasks:  make(chan Task, cfg.queueSize),
		errs:   make(chan error, cfg.errBuf),
		ctx:    ctx,
		cancel: cancel,
		closed: make(chan struct{}),
	}

	p.wg.Add(n)
	for i := 0; i < n; i++ {
		go p.worker()
	}

	// Close the error channel once every worker has returned, so callers
	// can safely `range` over Errors() without racing worker sends.
	go func() {
		p.wg.Wait()
		close(p.errs)
	}()

	return p
}

func (p *Pool) worker() {
	defer p.wg.Done()
	for {
		select {
		case <-p.ctx.Done():
			return
		case task, ok := <-p.tasks:
			if !ok {
				return
			}
			if err := task(p.ctx); err != nil {
				select {
				case p.errs <- err:
				case <-p.ctx.Done():
					return
				}
			}
		}
	}
}

// Submit queues a task for execution. It returns ErrPoolClosed once the
// pool has been shut down, p.ctx.Err() if the pool's own context ends
// first, or ctx.Err() if the supplied ctx is done before the task could be
// queued.
func (p *Pool) Submit(ctx context.Context, task Task) error {
	select {
	case <-p.closed:
		return ErrPoolClosed
	default:
	}

	select {
	case p.tasks <- task:
		return nil
	case <-p.closed:
		return ErrPoolClosed
	case <-p.ctx.Done():
		return p.ctx.Err()
	case <-ctx.Done():
		return ctx.Err()
	}
}

// Errors returns the channel task errors are delivered on. It is closed
// once all worker goroutines have exited (after Shutdown or Stop
// completes), so it is safe to range over.
func (p *Pool) Errors() <-chan error {
	return p.errs
}

// Shutdown stops the pool from accepting new tasks and waits for
// already-queued and in-flight tasks to finish, or for ctx to be done,
// whichever happens first. If ctx ends first, the pool's context is
// cancelled to interrupt any tasks still running, mirroring Stop. Shutdown
// is safe to call multiple times and from multiple goroutines; only the
// first call closes the task queue.
func (p *Pool) Shutdown(ctx context.Context) error {
	p.closeOnce.Do(func() {
		close(p.closed)
		close(p.tasks)
	})

	done := make(chan struct{})
	go func() {
		p.wg.Wait()
		close(done)
	}()

	select {
	case <-done:
		p.cancel()
		return nil
	case <-ctx.Done():
		p.cancel()
		return ctx.Err()
	}
}

// Stop immediately cancels the pool's context — interrupting in-flight
// tasks that observe ctx.Done() — discards any queued-but-not-started
// tasks, and blocks until every worker goroutine has returned. It is safe
// to call multiple times and from multiple goroutines.
func (p *Pool) Stop() {
	p.closeOnce.Do(func() {
		close(p.closed)
		close(p.tasks)
	})
	p.cancel()
	p.wg.Wait()
}
