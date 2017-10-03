package ch.ethz.ivt.sccer.planfeatures;

import org.matsim.api.core.v01.Scenario;
import org.matsim.core.config.ConfigUtils;
import org.matsim.core.population.io.PopulationReader;
import org.matsim.core.scenario.ScenarioUtils;

/**
 * @author thibautd
 */
public class WriteSccerPlanFeatures {
	public static void main( final String... args ) {
		final String populationFile = args[ 0 ];
		final String outputFile = args[ 1 ];

		final Scenario scenario = ScenarioUtils.createScenario( ConfigUtils.createConfig() );
		new PopulationReader( scenario ).readFile( populationFile );

		new PlanFeatureExtractor()
				.withFeature(
						"longest_stop_s",
						Features::longestStopTimeBetweenCarTrips )
				.withFeature(
						"longest_trip_m",
						Features::longestCarTrip_m )
				.withFeature(
						"total_stop_m",
						Features::totalStopTimeBetweenCarTrips )
				.withFeature(
						"total_trip_m",
						Features::totalCarTraveledDistance_m )
				.writeFeatures(
						scenario.getPopulation(),
						outputFile );
	}
}
