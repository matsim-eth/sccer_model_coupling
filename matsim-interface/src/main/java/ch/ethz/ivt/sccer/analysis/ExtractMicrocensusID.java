package ch.ethz.ivt.sccer.analysis;

import org.matsim.api.core.v01.Scenario;
import org.matsim.api.core.v01.population.Person;
import org.matsim.core.config.CommandLine;
import org.matsim.core.config.Config;
import org.matsim.core.config.ConfigUtils;
import org.matsim.core.population.io.PopulationReader;
import org.matsim.core.scenario.ScenarioUtils;

import java.io.BufferedWriter;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.OutputStreamWriter;

public class ExtractMicrocensusID {
    public static void main(String[] args) throws CommandLine.ConfigurationException, IOException {
        CommandLine cmd = new CommandLine.Builder(args) //
                .requireOptions("population-path", "output-path")
                .build();

        String populationPath = cmd.getOptionStrict("population-path");
        String outputPath = cmd.getOptionStrict("output-path");
        new ExtractMicrocensusID().run(populationPath, outputPath);

    }

    private void run(String populationPath, String outputPath) throws IOException {

        Config config = ConfigUtils.createConfig();
        Scenario scenario = ScenarioUtils.createScenario(config);
        new PopulationReader(scenario).readFile(populationPath);

        BufferedWriter writer = new BufferedWriter(new OutputStreamWriter(new FileOutputStream(outputPath)));

        writer.write(formatHeader() + "\n");
        writer.flush();

        for (Person person : scenario.getPopulation().getPersons().values()) {
            if (person.getAttributes().getAsMap().containsKey("mzPersonId")) {
                writer.write(formatEntry(person.getId().toString(),
                        person.getAttributes().getAttribute("mzPersonId").toString()) + "\n");
                writer.flush();
            }
        }

        writer.flush();
        writer.close();

    }

    private String formatHeader() {
        return String.join(";", new String[] { //
                "person_id", //
                "mz_person_id"
        });
    }

    private String formatEntry(String person_id, String mz_person_id) {
        return String.join(";", new String[] { //
                person_id,
                mz_person_id.toString()//
        });
    }
}
