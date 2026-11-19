/* GPL-3.0-or-later. TrueCombat: Platinum feel check: a deterministic clock for the game module.
 *
 * Linked into qagame only in feel-check builds (-Wl,--wrap=clock_gettime,--wrap=time). The game reads
 * the real clock for bot path-search budgets, perf metrics, weather seeds and match ids; in a feel
 * check every one of those must come out the same on every run. clock_gettime advances 1 microsecond
 * per call and time() is a fixed date, so time-sliced work depends only on how often it is asked. */
#include <time.h>

static long long feelNow = 1000000000LL;   /* nanoseconds */

int __wrap_clock_gettime(clockid_t id, struct timespec *t)
{
    (void)id;
    feelNow += 1000;
    t->tv_sec = (time_t)(feelNow / 1000000000LL);
    t->tv_nsec = (long)(feelNow % 1000000000LL);
    return 0;
}

time_t __wrap_time(time_t *out)
{
    const time_t fixed = 1798761600;   /* 2027-01-01 00:00:00 UTC */
    if (out) *out = fixed;
    return fixed;
}
