"""Find modular nth roots."""


def _is_prime(value):
    if value < 2:
        return False
    divisor = 2
    while divisor * divisor <= value:
        if value % divisor == 0:
            return False
        divisor += 1
    return True


def nthroot_mod(a, n, modulus, *, all_roots=False):
    """Return roots of ``x ** n == a (mod modulus)``.

    With ``all_roots=False`` return the least root or ``None``. Otherwise
    return every root in increasing order.
    """
    if type(a) is not int or type(n) is not int or type(modulus) is not int:
        raise TypeError("a, n and modulus must be integers")
    if n < 1 or modulus < 2 or type(all_roots) is not bool:
        raise ValueError("invalid root parameters")
    if not _is_prime(modulus):
        raise NotImplementedError("only prime moduli are supported")
    target = a % modulus
    roots = [value for value in range(modulus)
             if pow(value, n, modulus) == target]
    if all_roots:
        return roots
    return roots[0] if roots else None
