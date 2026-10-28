# Catch the AI (about 8 minutes)

We asked for a function that gives the forward exchange rate from covered interest parity, and
tests for it. `cip.py` and `test_cip.py` are the kind of code an agent writes: they look right, and
both tests pass. **We planted one mistake.** Find it the way you will check your own app.

Work in your team on one laptop. Open the terminal with Ctrl+` (Cmd+` on a Mac).

1. Run `pytest exercise`. It says `2 passed`.
2. Get the number another way: the exam question you know. Today the 2-year USD risk-free zero
   rate is 4.6% per annum and the 2-year EUR rate is 2.4% per annum, both continuously compounded.
   The spot exchange rate is $0.99/EUR. (a) What is the theoretical two-year forward exchange rate?
   Work it out by hand, to four decimals.
3. Ask Copilot (chat icon, then Agent):
   > Add a test to exercise/test_cip.py: with spot 0.99 USD per EUR and 2-year continuously
   > compounded rates of 4.6% (USD) and 2.4% (EUR), forward_rate must equal ______ USD per EUR, the
   > forward I computed by hand (within 0.0001). Do not change cip.py yet.

   Run `pytest exercise` again. What does the function return?
4. Ask Copilot to explain the difference and fix `cip.py`. Run `pytest exercise` once more.
   What happens to each of the first two tests now? Why?
5. If you finish early: market maker Mark quotes a two-year forward of $1.06/EUR. (b) What
   arbitrage exists? (c) Ask Copilot for a function that gives the profit when you borrow 1,000 USD
   or 1,000 EUR, and check every cash flow against your own answer.
6. Beyond the exam: express Mark's quote as a deviation from CIP. The USD rate implied by his
   forward is r_EUR + ln(F/S)/T. How many basis points is it above the 4.6% USD rate? In real
   markets that gap, the cross-currency basis, has stayed away from zero since 2008, widest at
   quarter-ends, in large part because bank balance sheets are costly (Du, Tepper and Verdelhan, 2018, *Journal
   of Finance*). An app could track it over time with quoted forwards and interest rates.

No Codespace yet? Do step 2 on paper and read `cip.py` on GitHub.

This folder is separate from the app: `pytest` on its own still runs only `tests/` (30 tests).
