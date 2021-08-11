function setAdmin(const admin : address; var s : storage) : return is
block {
    if Tezos.sender = s.admin then st.admin := admin
    else failwith("Only the admin can run this function");
} with (noOperations, store)
