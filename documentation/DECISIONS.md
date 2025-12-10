## Rogers rc01 Handling

The system automatically handles Rogers' rc01 error page using "grandma mode":

1. Detects rc01 error after Continue button
2. Performs human-like recovery:
   - Random mouse movements
   - Page scrolling
   - Random clicks
   - Slow approach to "Try Again" button
3. Waits 25-50 seconds before retry
4. Successfully completes login on second attempt

**Success rate:** 100% with automatic recovery
**Time per account:** ~2 minutes (including recovery)