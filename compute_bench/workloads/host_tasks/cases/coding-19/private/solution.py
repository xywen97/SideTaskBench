"""Find modular nth roots."""


def _factor_prime_powers(value):
    factors = []
    divisor = 2
    while divisor * divisor <= value:
        if value % divisor:
            divisor = 3 if divisor == 2 else divisor + 2
            continue
        power = 1
        while value % divisor == 0:
            value //= divisor
            power *= divisor
        factors.append((divisor, power))
        divisor = 3 if divisor == 2 else divisor + 2
    if value > 1:
        factors.append((value, value))
    return factors


def _roots_prime_power(a, n, prime, prime_power):
    roots = [value for value in range(prime)
             if pow(value, n, prime) == a % prime]
    base = prime
    while base < prime_power:
        next_base = base * prime
        roots = [candidate
                 for root in roots
                 for candidate in (root + offset * base for offset in range(prime))
                 if pow(candidate, n, next_base) == a % next_base]
        base = next_base
    return roots


def _inverse(value, modulus):
    old_r, r = value, modulus
    old_s, s = 1, 0
    while r:
        quotient = old_r // r
        old_r, r = r, old_r - quotient * r
        old_s, s = s, old_s - quotient * s
    return old_s % modulus


def _combine(left_roots, left_modulus, right_roots, right_modulus):
    inverse = _inverse(left_modulus % right_modulus, right_modulus)
    modulus = left_modulus * right_modulus
    combined = []
    for left in left_roots:
        for right in right_roots:
            step = ((right - left) * inverse) % right_modulus
            combined.append((left + left_modulus * step) % modulus)
    return sorted(set(combined)), modulus


def nthroot_mod(a, n, modulus, *, all_roots=False):
    """Return roots of ``x ** n == a (mod modulus)``.

    With ``all_roots=False`` return the least root or ``None``. Otherwise
    return every root in increasing order.
    """
    if type(a) is not int or type(n) is not int or type(modulus) is not int:
        raise TypeError("a, n and modulus must be integers")
    if n < 1 or modulus < 2 or type(all_roots) is not bool:
        raise ValueError("invalid root parameters")

    roots, combined_modulus = [0], 1
    for prime, prime_power in _factor_prime_powers(modulus):
        local = _roots_prime_power(a, n, prime, prime_power)
        if not local:
            roots = []
            break
        roots, combined_modulus = _combine(
            roots, combined_modulus, local, prime_power)
    if all_roots:
        return roots
    return roots[0] if roots else None
