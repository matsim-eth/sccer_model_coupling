package ch.ethz.ivt.sccer.analysis;

import org.matsim.api.core.v01.Id;
import org.matsim.api.core.v01.population.Person;

public class DefaultPersonAnalysisFilter implements PersonAnalysisFilter {
	@Override
	public boolean analyzePerson(Id<Person> personId) {
		return true;
	}
}
