package ch.ethz.ivt.sccer.planfeatures;

import org.apache.log4j.Logger;
import org.matsim.api.core.v01.population.Person;
import org.matsim.api.core.v01.population.Plan;
import org.matsim.api.core.v01.population.Population;
import org.matsim.core.utils.io.IOUtils;
import org.matsim.core.utils.misc.Counter;

import java.io.BufferedWriter;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.util.ArrayList;
import java.util.List;
import java.util.function.Function;
import java.util.function.ToDoubleFunction;

/**
 * @author thibautd
 */
public class PlanFeatureExtractor {
	private static final Logger log = Logger.getLogger( PlanFeatureExtractor.class );
	private final List<Feature> features = new ArrayList<>();

	public PlanFeatureExtractor withFeature( String name , Function<Plan,String> function ) {
		features.add( new Feature( name , function ) );
		return this;
	}

	public PlanFeatureExtractor withFeature( String name , ToDoubleFunction<Plan> function ) {
		return withFeature(
				name,
				(Plan plan) -> ""+function.applyAsDouble( plan ) );
	}

	public void writeFeatures( Population population , String file ) {
		log.info( "Extract features in file "+file );
		log.info( "Extract the following features: "+features.stream().map( f -> f.name ).reduce( "" , (s1,s2) -> s1+", "+s2 ) );
		final Counter counter = new Counter( "Extract features for agent # " , " / "+population.getPersons().size() );
		try ( BufferedWriter writer = IOUtils.getBufferedWriter( file ) ) {
			writer.write( "agentId" );
			writer.write( "\t" + "age" );
			writer.write( "\t" + "sex" );
			writer.write( "\t" + "mzHeadId" );
			writer.write( "\t" + "mzPersonId" );
			writer.write( "\t" + "statpopHouseholdId" );
			writer.write( "\t" + "statpopPersonId" );
			for ( Feature f : features ) {
				writer.write( "\t"+f.name );
			}

			for ( Person person : population.getPersons().values() ) {
				if (!person.getId().toString().contains("freight")) {
					counter.incCounter();
					final Plan plan = person.getSelectedPlan();

					writer.newLine();
					writer.write( person.getId().toString() );
					writer.write( "\t" + person.getAttributes().getAttribute("age").toString() );
					writer.write( "\t" + person.getAttributes().getAttribute("sex").toString() );
					writer.write( "\t" + person.getAttributes().getAttribute("mzHeadId").toString() );
					writer.write( "\t" + person.getAttributes().getAttribute("mzPersonId").toString() );
					writer.write( "\t" + person.getAttributes().getAttribute("statpopHouseholdId").toString() );
					writer.write( "\t" + person.getAttributes().getAttribute("statpopPersonId").toString() );
					for ( Feature feature : features ) writer.write( "\t"+feature.function.apply( plan ) );
				}
			}
			counter.printCounter();
		}
		catch ( IOException e ) {
			throw new UncheckedIOException( e );
		}
	}

	private static class Feature {
		private final String name;
		private final Function<Plan,String> function;

		private Feature(
				final String name,
				final Function<Plan, String> function ) {
			this.name = name;
			this.function = function;
		}
	}

}
