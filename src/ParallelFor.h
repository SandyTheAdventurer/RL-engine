#pragma once
#include <condition_variable>
#include <cstdint>
#include <functional>
#include <mutex>
#include <thread>
#include <vector>

// Persistent worker pool replacing OpenMP: PyTorch bundles its own OpenMP
// runtime, and loading a second one into the process (brew libomp on macOS,
// MSVC vcomp on Windows) segfaults or corrupts state. Plain std::thread
// shares no runtime with torch, so the conflict cannot occur.
class ParallelFor {
public:
    explicit ParallelFor(unsigned num_threads)
        : nthreads(num_threads == 0 ? 1 : num_threads) {
        workers.reserve(nthreads);
        for (unsigned t = 0; t < nthreads; ++t)
            workers.emplace_back([this, t] { worker_loop(t); });
    }

    ~ParallelFor() {
        {
            std::lock_guard<std::mutex> lk(m);
            stop = true;
        }
        cv_start.notify_all();
        for (auto& w : workers) w.join();
    }

    ParallelFor(const ParallelFor&) = delete;
    ParallelFor& operator=(const ParallelFor&) = delete;

    // Runs fn(0..n-1) across the pool; blocks until every index is done.
    void run(int n, const std::function<void(int)>& fn) {
        std::unique_lock<std::mutex> lk(m);
        job_n = n;
        job_fn = &fn;
        remaining = static_cast<int>(nthreads);
        ++generation;
        cv_start.notify_all();
        cv_done.wait(lk, [this] { return remaining == 0; });
        job_fn = nullptr;
    }

private:
    void worker_loop(unsigned tid) {
        const unsigned stride = nthreads;
        uint64_t seen = 0;
        for (;;) {
            const std::function<void(int)>* fn;
            int n;
            {
                std::unique_lock<std::mutex> lk(m);
                cv_start.wait(lk, [&] { return stop || generation != seen; });
                if (stop) return;
                seen = generation;
                fn = job_fn;
                n = job_n;
            }
            for (int i = static_cast<int>(tid); i < n; i += static_cast<int>(stride))
                (*fn)(i);
            {
                std::lock_guard<std::mutex> lk(m);
                if (--remaining == 0) cv_done.notify_one();
            }
        }
    }

    const unsigned nthreads;
    std::vector<std::thread> workers;
    std::mutex m;
    std::condition_variable cv_start, cv_done;
    const std::function<void(int)>* job_fn = nullptr;
    int job_n = 0;
    int remaining = 0;
    uint64_t generation = 0;
    bool stop = false;
};
