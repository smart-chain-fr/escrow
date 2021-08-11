#include "TypesEscrow.ligo"

function setAdmin(const admin : address; var s : storage) : return is
block {
    if Tezos.sender = s.admin then s.admin := admin
    else failwith("Only the admin can run this function");
} with (noOperations, s)


function initialize_escrow(const params : initialize_escrow_params; var s : storage) : return is
block {
    if Tezos.amount =/= params.price then failwith(notEnoughTez)
    else skip;
    s.escrows[params.id] := record [
        buyer = Tezos.sender;
        seller = params.seller;
        broker = params.broker;
        product = params.product;
        price = params.price;
        comment = map[
            "buyer" -> "";
            "seller" -> ""
        ];
        state = "Initialized!"; // Passer à un genre d'énum (map probablement)
        time = Tezos.now
    ]
} with (noOperations, s)

