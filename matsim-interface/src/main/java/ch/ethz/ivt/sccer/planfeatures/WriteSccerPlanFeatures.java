package ch.ethz.ivt.sccer.planfeatures;

import org.apache.log4j.Logger;
import org.matsim.api.core.v01.Id;
import org.matsim.api.core.v01.Scenario;
import org.matsim.api.core.v01.population.Person;
import org.matsim.api.core.v01.population.Plan;
import org.matsim.core.config.ConfigUtils;
import org.matsim.core.controler.ReplayEvents;
import org.matsim.core.events.EventsManagerModule;
import org.matsim.core.network.io.MatsimNetworkReader;
import org.matsim.core.population.io.PopulationReader;
import org.matsim.core.scenario.ScenarioByInstanceModule;
import org.matsim.core.scenario.ScenarioUtils;
import org.matsim.core.scoring.ExperiencedPlansModule;
import org.matsim.core.scoring.ExperiencedPlansService;
import org.matsim.core.scoring.functions.CharyparNagelScoringFunctionModule;

import java.util.ArrayList;
import java.util.Map;

/**
 * @author thibautd
 */
public class WriteSccerPlanFeatures {
	private static final Logger log = Logger.getLogger( WriteSccerPlanFeatures.class );
	private static final double TIME_STEP = 60 * 60;

	public static void main( final String... args ) {
		final String populationFile = args[ 0 ];
		final String networkFile = args[ 1 ];
		final String eventsFile = args[ 2 ];
		final String outputFile = args[ 3 ];

		//if ( new File( outputFile ).exists() ) throw new RuntimeException( "file "+outputFile+" exists." );

		log.info( "Read population" );
		final Scenario scenario = ScenarioUtils.createScenario( ConfigUtils.createConfig() );
		new PopulationReader( scenario ).readFile( populationFile );

		log.info( "Read network" );
		new MatsimNetworkReader( scenario.getNetwork() ).readFile( networkFile );

		log.info( "Extract experienced plans" );
		final ReplayEvents.Results results = replacePlansByExperiencedPlans(scenario, eventsFile);

		log.info( "Extract features" );
		PlanFeatureExtractor extractor =
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
								Features::totalCarTraveledDistance_m );

		final TravelDistanceEventHandler distances = results.get(TravelDistanceEventHandler.class);
		for ( double s=0; s < 24 * 3600; s += TIME_STEP ) {
			extractor.withFeature(
					"driven_s_["+s+";"+(s+TIME_STEP)+"]",
					Features.driveTimeInInterval( s , s + TIME_STEP ));
			extractor.withFeature(
					"distance_m_["+s+";"+(s+TIME_STEP)+"]",
					distances.distanceFeature( s , s + TIME_STEP ));
		}

		extractor.writeFeatures(
						scenario.getPopulation(),
						outputFile );

		log.info("Done");
	}

	public static ReplayEvents.Results replacePlansByExperiencedPlans(
			final Scenario scenario,
			final String eventsFile ) {

		final ReplayEvents.Results replay =
				ReplayEvents.run(scenario.getConfig(),
						eventsFile,
						new ScenarioByInstanceModule(scenario),
						new ExperiencedPlansModule(),
						new CharyparNagelScoringFunctionModule(),
						new EventsManagerModule(),
						new ReplayEvents.Module(),
						new TravelDistanceEventHandler.Module());

		ExperiencedPlansService experiencedPlansService = replay.get( ExperiencedPlansService.class );

		final Map<Id<Person>,Plan> experiencedPlans = experiencedPlansService.getExperiencedPlans();

		for ( final Person person : scenario.getPopulation().getPersons().values() ) {
			final Plan plan = experiencedPlans.get( person.getId() );
			if ( plan == null ) continue;
			for ( Plan toRemove : new ArrayList<>( person.getPlans() ) ) person.removePlan( toRemove );
			person.addPlan( plan );
			person.setSelectedPlan( plan );
		}

		return replay;
	}
}
