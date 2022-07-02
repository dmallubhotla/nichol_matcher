# Nichol paper dipole configuration creator

Utility repo that uses `pdme` to find matching configurations of dipoles for this [Nichol group paper](https://www.nature.com/articles/s41467-022-28519-x.pdf)'s data.
Data for charge noise spectrum comes from Fig. 5 there.

`processedNicholData.csv` unsurprisingly contains a processed version of the Nichol data.
First, the points in their Matlab `.fig` file are extracted.
The data is first scaled up by a factor of $10^14.
This changes the units to make the scale centred around 1.
Then, the data is binned in log-space, and each bin is represented by its log-space mean.
Additionally, for each bin the points three standard deviations below and above the mean are computed as well.
Each row in `processedNicholData.csv` represents a bin, with the four columns being $f$, $S(f)$, $S(f) - 3\sigma$ and $S(f) + 3\sigma$.

`frequency_inputs.txt` contains a text file with just the frequency inputs for each of the bins.
This is redundant and is just for convenience with `pdme`'s somewhat odd API.

## Setup and Usage

Depending on your python configuration, you might have to do something funky.
The simplest thing is to have `poetry` installed, then run `poetry install`.
Then, from within the `matching` directory, run `poetry run python match_z_fewer` or similar.
Relative paths mean running from there is necessary.

Flags within `match_z_fewer` control the number of Monte Carlo simulation steps, which can be useful.
If your CPU usage stays low, then python likely cannot acquire memory and the calculation will hang.

The output file is a list of configurations of dipoles.
Each line represents a single configuration of dipoles that generates a spectrum compatible with data in the paper.
Within each line, each child element represents a single dipole as 7 elements.
The 7 elements are, respectively
1. $p_x$, the dipole moment in the x direction, in units that absorb all prefactors
2. $p_y$
3. $p_z$
4. $s_x$, the dipole position in the x direction, in units of 10 nanometre
5. $s_y$
6. $s_z$
7. $w$, the dipole relaxation rate, in Hz

The dipole moment units are such that $S \propto \vec{p} \cdot s$ etc.
Note that the qubit is set to be at the origin in the Nichol paper.

## References
- Connors, E.J., Nelson, J., Edge, L.F. et al. Charge-noise spectroscopy of Si/SiGe quantum dots via dynamically-decoupled exchange oscillations. Nat Commun 13, 940 (2022). https://doi.org/10.1038/s41467-022-28519-x
