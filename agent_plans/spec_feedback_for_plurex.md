# Feedback for plurex

Open feedback on the spec and paper behaviour, from the docs' point of view. Remove an item once a refresh confirms it
landed, and record that in the refresh log.

## The app says a new member has no access, but every member reads every account

At `d8bfc6821`, `UserInformationPoint` gives every member `MEMBER_ACCESS` (Read only on paper and real accounts) on top
of their own tree, and `SECURITY.md` says "A member can read, plus their own tree". The app says otherwise in three
places: Members says "Each member has their own access, and starts with none", Invite says they "join with no access
until you give them some", and the Member access editor shows **No access** for real accounts while the member can read
them.

The docs follow the code: every member reads every account, and the editor adds to it. Either drop `MEMBER_ACCESS`, so
the editor is the whole truth, or say in the app that members always read every account, and show it in the editor.
