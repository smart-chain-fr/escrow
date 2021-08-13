#include "../partials/MethodEscrow.ligo"

function main (const action : escrowAction; const s : storage) : return is
    case action of
    | Agree(id)                     -> agree(id, s)
    | Initialize_escrow(parameters) -> initialize_escrow(parameters, s)
    | SetAdmin(admin)               -> setAdmin(admin, s)
    | Cancel_escrow(id)             -> cancel_escrow(id, s)
    | Receive_item(params)          -> receive_item(params, s)
    | AddComment(comment)           -> addComment(comment,s)
    end;