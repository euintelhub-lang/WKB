# workerpool

A small, dependency-free Go package implementing a fixed-size concurrent
worker pool with graceful shutdown.

## Usage

```go
ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
defer stop()

pool := workerpool.New(ctx, 4) // 4 workers

pool.Submit(ctx, func(ctx context.Context) error {
    // do work, respecting ctx.Done() for cancellation
    return nil
})

// on shutdown signal:
shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
defer cancel()
if err := pool.Shutdown(shutdownCtx); err != nil {
    pool.Stop() // deadline hit — force-cancel whatever is still running
}
```

- `Submit` queues a task; it blocks (or fails with the queue's context
  error) once the queue is full, per `WithQueueSize`.
- `Shutdown(ctx)` stops accepting new tasks and waits for queued and
  in-flight tasks to finish, up to `ctx`'s deadline. It's the graceful
  path.
- `Stop()` cancels immediately, discards anything still queued, and waits
  for running tasks to observe cancellation and return. Use it as a
  fallback when `Shutdown` times out, or when an immediate stop is wanted.
- `Errors()` returns a channel of errors returned by tasks; it closes once
  every worker has exited, so it's safe to `range` over.

See `cmd/example/main.go` for a full program wiring this up to OS signals.

## Running

```sh
go run ./cmd/example      # Ctrl-C to trigger graceful shutdown
go test ./...
```
