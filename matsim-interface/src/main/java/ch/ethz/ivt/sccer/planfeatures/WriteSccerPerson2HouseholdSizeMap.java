package ch.ethz.ivt.sccer.planfeatures;

import org.apache.log4j.Logger;
import org.matsim.api.core.v01.Id;
import org.matsim.api.core.v01.Scenario;
import org.matsim.api.core.v01.population.Person;
import org.matsim.core.config.ConfigUtils;
import org.matsim.core.population.io.PopulationReader;
import org.matsim.core.scenario.ScenarioUtils;
import org.matsim.core.utils.io.IOUtils;
import org.matsim.core.utils.misc.Counter;
import org.matsim.households.Household;
import org.matsim.households.HouseholdsReaderV10;

import java.io.BufferedWriter;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.util.HashMap;
import java.util.Map;

public class WriteSccerPerson2HouseholdSizeMap {
    private static final Logger log = Logger.getLogger( WriteSccerPerson2HouseholdSizeMap.class );


    public static void main(String[] args) {
        final String populationFile = args[ 0 ];
        final String householdsFile = args[ 1 ];
        final String outputFile = args[ 2 ];

        log.info( "Read population" );
        final Scenario scenario = ScenarioUtils.createScenario( ConfigUtils.createConfig() );
        new PopulationReader( scenario ).readFile( populationFile );

        log.info( "Read households" );
        new HouseholdsReaderV10( scenario.getHouseholds() ).readFile( householdsFile );

        log.info( "Map household size to person ids" );
        Map<Id<Person>, Integer> persons2householdSize = new HashMap<>();
        for (Household household : scenario.getHouseholds().getHouseholds().values()) {
            for (Id<Person> personId : household.getMemberIds()) {
                if ( persons2householdSize.containsKey(personId) ) {
                    log.warn("Person already assigned to household...?");
                }

                persons2householdSize.put(personId, household.getMemberIds().size());
            }
        }

        log.info( "Write to file : " + outputFile );
        final Counter counter = new Counter( "Extract features for agent # " , " / " + scenario.getPopulation().getPersons().size() );
        try ( BufferedWriter writer = IOUtils.getBufferedWriter( outputFile ) ) {
            writer.write( "agentId" + "\t" + "householdSize");

            for ( Map.Entry<Id<Person>, Integer> entry : persons2householdSize.entrySet() ) {
                counter.incCounter();
                writer.newLine();
                writer.write(entry.getKey().toString());
                writer.write("\t");
                writer.write(Integer.toString(entry.getValue()));
            }
            counter.printCounter();
        }
        catch ( IOException e ) {
            throw new UncheckedIOException( e );
        }
    }

}
