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

public class WriteSccerHouseholdFeatures {
    private static final Logger log = Logger.getLogger( WriteSccerHouseholdFeatures.class );


    public static void main(String[] args) {
        final String populationFile = args[ 0 ];
        final String householdsFile = args[ 1 ];
        final String outputFile = args[ 2 ];

        log.info( "Read population" );
        final Scenario scenario = ScenarioUtils.createScenario( ConfigUtils.createConfig() );
        new PopulationReader( scenario ).readFile( populationFile );

        log.info( "Read households" );
        new HouseholdsReaderV10( scenario.getHouseholds() ).readFile( householdsFile );

        log.info( "Write to file : " + outputFile );
        final Counter counter = new Counter( "Extract features for agent # " , " / " + scenario.getPopulation().getPersons().size() );
        try ( BufferedWriter writer = IOUtils.getBufferedWriter( outputFile ) ) {
            writer.write( "agentId\thouseholdId\thouseholdSize\thouseholdIncome");

            for (Household household : scenario.getHouseholds().getHouseholds().values()) {
                for (Id<Person> personId : household.getMemberIds()) {
                    counter.incCounter();
                    writer.newLine();
                    writer.write(personId.toString());
                    writer.write("\t");
                    writer.write(household.getId().toString());
                    writer.write("\t");
                    writer.write(""+household.getMemberIds().size());
                    writer.write("\t");
                    writer.write(""+household.getIncome().getIncome());
                }
            }
            counter.printCounter();
        }
        catch ( IOException e ) {
            throw new UncheckedIOException( e );
        }

        log.info("Done");
    }

}
