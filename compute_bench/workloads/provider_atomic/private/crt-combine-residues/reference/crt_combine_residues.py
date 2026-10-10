def crt_combine_residues(residues, moduli):
    if len(residues) != len(moduli) or not moduli:
        raise ValueError("residues and moduli must be nonempty and of equal length")
    value, modulus = 0, 1
    for residue, mod in zip(residues, moduli):
        step = ((residue - value) * pow(modulus, -1, mod)) % mod
        value += modulus * step
        modulus *= mod
    return (value % modulus, modulus)
