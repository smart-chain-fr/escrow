#include "TypesEscrow.ligo"

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


function agree(const id : bytes; var s : storage) : return is
block {
    var esc : escrow := case s.escrows[id] of
        Some(_escrow) -> _escrow
        | None -> failwith("Escrow not found")
    end;
    if Tezos.sender =/= esc.buyer then failwith("Access denied")
    else skip;
    esc.state := "Completed";
    s.escrows[id] := esc;
    const receiver : contract (unit) = (case (Tezos.get_contract_opt ( esc.seller) : option(contract(unit))) of // wrapper ca dans une fonction 
        Some (receiver) -> receiver // wrapper ca dans une fonction 
        | None -> // wrapper ca dans une fonction 
        (failwith ("No contract.") // wrapper ca dans une fonction 
        : contract (unit))// wrapper ca dans une fonction 
    end);// wrapper ca dans une fonction 
    const op : operation = Tezos.transaction (unit, esc.price, receiver);// wrapper ca dans une fonction 
    const ops : list (operation) = list [op]
} with (ops, s)


function cancel_escrow(const id : bytes; var s : storage) : return is
block {
    var esc : escrow := case s.escrows[id] of
        Some(_escrow) -> _escrow
        | None -> failwith("Escrow not found")
    end;
    if not (Tezos.sender = esc.buyer or Tezos.sender = esc.seller) then failwith("Access denied")
    else skip;
    var cancel : cancel := case s.cancels[id] of
        Some(_cancel) -> _cancel
        | None -> map [ Tezos.sender -> True ]
    end;
    cancel[Tezos.sender] := True;
    const buy_cancel : bool = case cancel[esc.buyer] of
        Some(_val) -> _val
        | None -> False
    end;
    const sell_cancel : bool = case cancel[esc.seller] of
        Some(_val) -> _val
        | None -> False
    end;
    s.cancels[id] := cancel;
    var ops : list (operation) := list []; //sortir ca du if et pattern matching
    if buy_cancel and sell_cancel then
    block {
        const receiver : contract (unit) = (case (Tezos.get_contract_opt ( esc.buyer) : option(contract(unit))) of //wrapper ca dans une fonction
            Some (receiver) -> receiver //wrapper ca dans une fonction
            | None ->  //wrapper ca dans une fonction
            (failwith ("No contract.")  //wrapper ca dans une fonction
            : contract (unit)) //wrapper ca dans une fonction
        end); //wrapper ca dans une fonction
        remove id from map s.escrows;
        const op : operation = Tezos.transaction (unit, esc.price, receiver);// wrapper ca dans une fonction 
        ops := list [op];    
    }    
    else skip;
}   with(ops, s) //changer ca une opération peut etre execute

function setAdmin(const admin : address; var s : storage) : return is
block {
    if Tezos.sender = s.admin then s.admin := admin
    else failwith("Only the admin can run this function");
} with (noOperations, s);

