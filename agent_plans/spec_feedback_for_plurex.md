# Feedback for plurex

Open feedback on the spec and paper behaviour, from the docs' point of view. Remove an item once a refresh confirms it
landed, and record that in the refresh log.

## Paper Deposit, Withdraw and SetFeeTier can fail after they succeed

At `2bebadbca`, `ApiPaperRoutes` runs the command under `MANAGE_PAPER`, then reads the result back under `READ`
(`getWallets` for Deposit and Withdraw, `getPaperFeeSettings` for SetFeeTier). A key with **Deposit, withdraw and set fee
tier** but not **Read orders, portfolio and settings** gets `403 Forbidden` after the deposit or withdrawal has been
applied. Deposit and Withdraw are not safe to repeat, so a client that retries on the 403 moves the balance twice.

The docs tell readers to grant both, as the Full preset does. Either return the result without a second check, or check
`READ` before applying the command.

## ListAccounts does not say it filters by access

`ListAccounts` says "Lists your accounts, optionally filtered." It now returns only the accounts the key can see, and
filters after paging, so a page can be short or empty while `nextCursor` is set. A key with no access to an account
does not see it at all. One sentence in the description would make both visible in the reference.
