package ch.ethz.ivt.sccer.planfeatures;

import ch.ethz.ivt.sccer.experiencedplans.ExperiencedPlansCreator;
import org.apache.log4j.Logger;
import org.matsim.api.core.v01.Scenario;
import org.matsim.api.core.v01.population.Plan;
import org.matsim.core.config.ConfigUtils;
import org.matsim.core.network.io.MatsimNetworkReader;
import org.matsim.core.population.io.PopulationReader;
import org.matsim.core.scenario.ScenarioUtils;

import java.io.File;

/**
 * @author thibautd
 */
public class WriteSccerPlanFeatures {
	private static final Logger log = Logger.getLogger( WriteSccerPlanFeatures.class );

	public static void main( final String... args ) {
		final String populationFile = args[ 0 ];
		final String networkFile = args[ 1 ];
		final String eventsFile = args[ 2 ];
		final String outputFile = args[ 3 ];

		if ( new File( outputFile ).exists() ) throw new RuntimeException( "file "+outputFile+" exists." );

		log.info( "Read population" );
		final Scenario scenario = ScenarioUtils.createScenario( ConfigUtils.createConfig() );
		new PopulationReader( scenario ).readFile( populationFile );

		log.info( "Read network" );
		new MatsimNetworkReader( scenario.getNetwork() ).readFile( networkFile );

		log.info( "Extract experienced plans" );
		ExperiencedPlansCreator.replacePlansByExperiencedPlans( scenario , eventsFile );

		log.info( "Extract features" );
		new PlanFeatureExtractor()
				.withFeature(
						"longest_stop_s",
						Features::longestStopTimeBetweenCarTrips )
				.withFeature(
						"longest_stop_9_16_s",
						(Plan p) -> Features.longestStopTimeBetweenCarTripsInRange( p , 9 , 16 ) )
				.withFeature(
						"longest_trip_m",
						Features::longestCarTrip_m )
				.withFeature(
						"total_stop_s",
						Features::totalStopTimeBetweenCarTrips )
				.withFeature(
						"total_trip_m",
						Features::totalCarTraveledDistance_m )
				.writeFeatures(
						scenario.getPopulation(),
						outputFile );
	}
}
