import csv
import logging
import numpy
import itertools
import pdme
import pdme.inputs
import pdme.measurement
from pdme.model import (
	LogSpacedRandomCountMultipleDipoleFixedMagnitudeModel,
	LogSpacedRandomCountMultipleDipoleFixedMagnitudeFixedOrientationModel,
)
import pdme.util.fast_v_calc
import multiprocessing
import random
import datetime


_logger = logging.getLogger(__name__)

# We assume a four column CSV file, with a single, fixed dot position
# The four columns are
# frequency mean_value(irrelevant) lower_bound upper_bound
def read_measurement_csv(filename, dot_position):
	with open(filename, "r", newline="") as measurement_file:
		reader = csv.reader(measurement_file)
		floated_rows = [
			(float(a), float(b), float(c), float(d)) for a, b, c, d in reader
		]
		return [
			pdme.measurement.DotRangeMeasurement(
				f=f, v_low=v_low, v_high=v_high, r=dot_position
			)
			for f, _, v_low, v_high in floated_rows
		]


def get_a_result_fast_filter(input) -> int:
	model, dot_inputs, lows, highs, monte_carlo_count, seed = input

	rng = numpy.random.default_rng(seed)
	# TODO: A long term refactor is to pull the frequency stuff out from here. The None stands for max_frequency, which is unneeded in the actually useful models.
	sample_dipoles = model.get_monte_carlo_dipole_inputs(
		monte_carlo_count, None, rng_to_use=rng
	)

	current_sample = sample_dipoles
	for di, low, high in zip(dot_inputs, lows, highs):

		if len(current_sample) < 1:
			break
		vals = pdme.util.fast_v_calc.fast_vs_for_dipoleses(
			numpy.array([di]), current_sample
		)

		current_sample = current_sample[numpy.all((vals > low) & (vals < high), axis=1)]
	return current_sample


def main():

	# one dot, at the origin
	dot_positions = [[0, 0, 0]]

	freq = []
	with open("../frequency_inputs.txt", "r") as freq_file:
		freq = [float(l.strip()) for l in freq_file]
	inputs = pdme.inputs.inputs_with_frequency_range(dot_positions, freq)

	# All of these are awkward to read because of the non-named parameters.
	# The important thing is that all the distance units are in 10 nms, so this is where the specific geometry of the paper is encoded.
	def get_free_or_model(pfixexp, filled_slots, total_slots):
		m = LogSpacedRandomCountMultipleDipoleFixedMagnitudeModel(
			-10,
			10,
			-17.5,
			17.5,
			5,
			7.5,
			-5,
			6.5,
			10**pfixexp,
			total_slots,
			filled_slots / total_slots,
		)
		return (
			f"connors_geom-free_orientation-pfixexp_{pfixexp}-dipole_count_{filled_slots}-{total_slots}",
			m,
		)

	def get_fixed_or_z_model(pfixexp, filled_slots, total_slots):
		m = LogSpacedRandomCountMultipleDipoleFixedMagnitudeFixedOrientationModel(
			-10,
			10,
			-17.5,
			17.5,
			5,
			7.5,
			-5,
			6.5,
			10**pfixexp,
			0,
			0,
			total_slots,
			filled_slots / total_slots,
		)
		return (
			f"connors_geom-z_aligned-pfixexp_{pfixexp}-dipole_count_{filled_slots}-{total_slots}",
			m,
		)

	def get_fixed_or_x_model(pfixexp, filled_slots, total_slots):
		m = LogSpacedRandomCountMultipleDipoleFixedMagnitudeFixedOrientationModel(
			-10,
			10,
			-17.5,
			17.5,
			5,
			7.5,
			-5,
			6.5,
			10**pfixexp,
			numpy.pi / 2,
			0,
			total_slots,
			filled_slots / total_slots,
		)
		return (
			f"connors_geom-x_aligned-pfixexp_{pfixexp}-dipole_count_{filled_slots}-{total_slots}",
			m,
		)

	# This is the important guy.
	# This sets what model is being used for finding matches.
	# This picks whether it's a fixed orientation in the x/z direction vs free orientation.
	# The first parameter is the log magnitude of the dipoles in an awkward unit
	model_to_test = get_fixed_or_z_model(3.5, 31, 40)

	real_measurements = read_measurement_csv("../processedNicholData.csv", (0, 0, 0))
	dot_inputs = [(measure.r, measure.f) for measure in real_measurements]

	dot_inputs_array = pdme.measurement.input_types.dot_inputs_to_array(dot_inputs)

	(
		lows,
		highs,
	) = pdme.measurement.input_types.dot_range_measurements_low_high_arrays(
		real_measurements
	)

	monte_carlo_count = 5000
	monte_carlo_cycles = 2750
	max_monte_carlo_cycles_steps = 20
	target_success = 10
	initial_seed = 42
	seed_sequence = numpy.random.SeedSequence(initial_seed)

	matches = []

	core_count = multiprocessing.cpu_count() - 1 or 1
	with multiprocessing.Pool(core_count) as pool:
		cycles = 0
		cycle_success = 0
		cycle_count = 0
		while (cycles < max_monte_carlo_cycles_steps) and (
			cycle_success <= target_success
		):
			_logger.debug(f"Starting cycle {cycles}")
			cycles += 1
			current_success = 0
			cycle_count += monte_carlo_count * monte_carlo_cycles

			# generate a seed from the sequence for each core.
			# note this needs to be inside the loop for monte carlo cycle steps!
			# that way we get more stuff.
			seeds = seed_sequence.spawn(monte_carlo_cycles)

			result_func = get_a_result_fast_filter
			_logger.debug("Starting pool run")
			raw_current_matches = list(pool.imap_unordered(
				result_func,
				[
					(
						model_to_test[1],
						dot_inputs_array,
						lows,
						highs,
						monte_carlo_count,
						seed,
					)
					for seed in seeds
				],
				50,
			))
			current_matches = [m for m in raw_current_matches if len(m)]
			_logger.info("finished pool run, got matches")
			_logger.debug(list(current_matches))
			current_success = sum(1 for m in current_matches if len(m))
			if len(current_matches):
				matches.append(current_matches)

			cycle_success += current_success
			_logger.debug(f"current running successes: {cycle_success}")
	_logger.info(matches)
	timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
	_logger.info(f"Writing to output-{timestamp}.txt")
	with open(f"output-{timestamp}.txt", "w") as output_file:
		for match_set in matches:
			for match in match_set:
				comma = ","
				newline = '\n'
				nothing = ''
				output_file.write(f"{numpy.array2string(match[0], max_line_width=numpy.inf, threshold=numpy.inf, separator=comma).replace(newline, nothing)}\n")

if __name__ == "__main__":
	logging.basicConfig(level=logging.DEBUG)
	logging.getLogger("pdme").setLevel(logging.INFO)
	main()
