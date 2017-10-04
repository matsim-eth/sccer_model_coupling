package ch.ethz.ivt.sccer.experiencedplans;

import org.matsim.api.core.v01.Id;
import org.matsim.api.core.v01.Scenario;
import org.matsim.api.core.v01.population.Person;
import org.matsim.api.core.v01.population.Plan;
import org.matsim.api.core.v01.population.Population;
import org.matsim.core.config.Config;
import org.matsim.core.config.ConfigUtils;
import org.matsim.core.controler.Injector;
import org.matsim.core.controler.ReplayEvents;
import org.matsim.core.events.EventsManagerModule;
import org.matsim.core.population.io.PopulationReader;
import org.matsim.core.scenario.ScenarioByInstanceModule;
import org.matsim.core.scenario.ScenarioUtils;
import org.matsim.core.scoring.EventsToActivities;
import org.matsim.core.scoring.EventsToLegs;
import org.matsim.core.scoring.ExperiencedPlansModule;
import org.matsim.core.scoring.ExperiencedPlansService;
import org.matsim.core.scoring.functions.CharyparNagelScoringFunctionModule;

import java.util.ArrayList;
import java.util.Map;

/**
 * @author thibautd
 */
public class ExperiencedPlansCreator {
	public static void replacePlansByExperiencedPlans(
			final Scenario scenario,
			final String eventsFile ) {

		com.google.inject.Injector injector = Injector.createInjector(scenario.getConfig(),
				new ScenarioByInstanceModule(scenario),
				new ExperiencedPlansModule(),
				new CharyparNagelScoringFunctionModule(),
				new EventsManagerModule(),
				new ReplayEvents.Module());

		injector.getInstance(ReplayEvents.class).playEventsFile( eventsFile, 1);
		ExperiencedPlansService experiencedPlansService = injector.getInstance( ExperiencedPlansService.class );
		final Map<Id<Person>,Plan> experiencedPlans = experiencedPlansService.getExperiencedPlans();

		for ( final Person person : scenario.getPopulation().getPersons().values() ) {
			final Plan plan = experiencedPlans.get( person.getId() );
			if ( plan == null ) continue;
			for ( Plan toRemove : new ArrayList<>( person.getPlans() ) ) person.removePlan( toRemove );
			person.addPlan( plan );
			person.setSelectedPlan( plan );
		}
	}
}
