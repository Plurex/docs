# Feedback for plurex

Open feedback on the spec and paper behaviour, from the docs' point of view. Remove an item once a refresh confirms it
landed, and record that in the refresh log.

## Open orders are described as "live"

`hostsListOpenOrders` says "Lists live orders, globally or for one instrument." and `ListOpenOrdersRequest` says
"Lists the account's live orders." Since `Pending` was added (3c2850912), "live" reads as the `Live` state, but the
list returns every open order, `Pending` included (paper filters on non-terminal status; the app counts `Pending` as
open). Suggest "Lists open orders (`Pending` or `Live`), globally or for one instrument." and "Lists the account's
open orders." The docs say `Pending` and `Live` in `guides/orders` meanwhile.
