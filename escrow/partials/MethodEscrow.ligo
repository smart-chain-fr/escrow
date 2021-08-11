function setAdmin(const admin : address; var store : storage) : return is
block {
    if Tezos.sender = store.admin then store.admin := admin
    else failwith("Only the admin can run this function");
} with (noOperations, store)