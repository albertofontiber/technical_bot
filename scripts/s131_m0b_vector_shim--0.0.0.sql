\echo Use "CREATE EXTENSION vector" to load this file. \quit

-- This is deliberately not pgvector. It preserves vector(N) type modifiers and
-- the <=> signature so PostgreSQL can parse and execute the S117/S131 catalog,
-- role, RLS and rollback tests on a disposable Windows cluster. It returns a
-- constant distance and must never be used for vector correctness or recall.
CREATE TYPE extensions.vector;

CREATE FUNCTION extensions.vector_in(cstring, oid, integer)
RETURNS extensions.vector
LANGUAGE internal IMMUTABLE STRICT PARALLEL SAFE
AS 'varcharin';

CREATE FUNCTION extensions.vector_out(extensions.vector)
RETURNS cstring
LANGUAGE internal IMMUTABLE STRICT PARALLEL SAFE
AS 'varcharout';

CREATE FUNCTION extensions.vector_recv(internal, oid, integer)
RETURNS extensions.vector
LANGUAGE internal IMMUTABLE STRICT PARALLEL SAFE
AS 'varcharrecv';

CREATE FUNCTION extensions.vector_send(extensions.vector)
RETURNS bytea
LANGUAGE internal IMMUTABLE STRICT PARALLEL SAFE
AS 'varcharsend';

CREATE FUNCTION extensions.vector_typmod_in(cstring[])
RETURNS integer
LANGUAGE internal IMMUTABLE STRICT PARALLEL SAFE
AS 'varchartypmodin';

CREATE FUNCTION extensions.vector_typmod_out(integer)
RETURNS cstring
LANGUAGE internal IMMUTABLE STRICT PARALLEL SAFE
AS 'varchartypmodout';

CREATE TYPE extensions.vector (
    INPUT = extensions.vector_in,
    OUTPUT = extensions.vector_out,
    RECEIVE = extensions.vector_recv,
    SEND = extensions.vector_send,
    TYPMOD_IN = extensions.vector_typmod_in,
    TYPMOD_OUT = extensions.vector_typmod_out,
    INTERNALLENGTH = VARIABLE,
    ALIGNMENT = int4,
    STORAGE = extended,
    CATEGORY = 'U',
    COLLATABLE = false
);

CREATE FUNCTION extensions.vector_s131_constant_cosine(
    extensions.vector,
    extensions.vector
)
RETURNS double precision
LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE
AS $function$
    SELECT 0::double precision
$function$;

CREATE OPERATOR extensions.<=> (
    LEFTARG = extensions.vector,
    RIGHTARG = extensions.vector,
    FUNCTION = extensions.vector_s131_constant_cosine
);

COMMENT ON TYPE extensions.vector IS
'S131 disposable signature shim only; NOT pgvector and not valid for vector behavior.';
