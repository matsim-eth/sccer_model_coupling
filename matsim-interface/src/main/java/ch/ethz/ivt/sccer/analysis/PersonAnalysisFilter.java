package ch.ethz.ivt.sccer.analysis;

import org.matsim.api.core.v01.Id;
import org.matsim.api.core.v01.population.Person;

public interface PersonAnalysisFilter {
	boolean analyzePerson(Id<Person> personId);
}
