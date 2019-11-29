package ch.ethz.ivt.sccer.planfeatures;

import com.google.inject.Inject;
import gnu.trove.list.TDoubleList;
import gnu.trove.list.array.TDoubleArrayList;
import org.matsim.api.core.v01.Id;
import org.matsim.api.core.v01.events.*;
import org.matsim.api.core.v01.events.handler.*;
import org.matsim.api.core.v01.network.Link;
import org.matsim.api.core.v01.network.Network;
import org.matsim.api.core.v01.population.Person;
import org.matsim.api.core.v01.population.Plan;
import org.matsim.api.core.v01.population.Population;
import org.matsim.core.controler.AbstractModule;
import org.matsim.core.events.algorithms.Vehicle2DriverEventHandler;

import java.util.HashMap;
import java.util.Map;
import java.util.function.ToDoubleFunction;

/**
 * An event handler that stores traveled distance by car per time bin for each agent
 * @author thibautd
 */
public class TravelDistanceEventHandler implements
		LinkEnterEventHandler, LinkLeaveEventHandler,
		VehicleEntersTrafficEventHandler, VehicleLeavesTrafficEventHandler {
	private final Vehicle2DriverEventHandler vehicle2Driver = new Vehicle2DriverEventHandler();
	private final Population population;
	private final Network network;
	private final Map<Id<Person>,PersonRecord> records = new HashMap<>();

	// TODO make configurable
	private final double binSize = 60 * 60;

	public static class Module extends AbstractModule {
		@Override
		public void install() {
			bind(TravelDistanceEventHandler.class).asEagerSingleton();
			addEventHandlerBinding().to(TravelDistanceEventHandler.class);
		}
	}

	@Inject
	public TravelDistanceEventHandler(Population population, Network network) {
		this.population = population;
		this.network = network;
	}

	public PersonRecord getRecord(Id<Person> person) {
		return records.computeIfAbsent(person, PersonRecord::new);
	}

	public ToDoubleFunction<Plan> distanceFeature(final double start, final double end) {
		return (Plan p) -> getRecord(p.getPerson().getId()).calcTraveledDistance(start, end);
	}

	@Override
	public void handleEvent(LinkEnterEvent event) {
		final Id<Person> person = vehicle2Driver.getDriverOfVehicle(event.getVehicleId());
		if (!population.getPersons().containsKey(person)) return;
		final PersonRecord record = records.computeIfAbsent(person, PersonRecord::new);
		record.start(event.getTime());
	}

	@Override
	public void handleEvent(LinkLeaveEvent event) {
		final Id<Person> person = vehicle2Driver.getDriverOfVehicle(event.getVehicleId());
		if (!population.getPersons().containsKey(person)) return;
		final PersonRecord record = records.computeIfAbsent(person, PersonRecord::new);
		final double length = getLength(event.getLinkId());
		record.end(event.getTime(), length);
	}

	@Override
	public void reset(int iteration) {
		vehicle2Driver.reset(iteration);
	}

	@Override
	public void handleEvent(VehicleEntersTrafficEvent event) {
		if (!population.getPersons().containsKey(event.getPersonId())) return;
		vehicle2Driver.handleEvent(event);

		final PersonRecord record = records.computeIfAbsent(event.getPersonId(), PersonRecord::new);
		record.start(event.getTime());
	}

	@Override
	public void handleEvent(VehicleLeavesTrafficEvent event) {
		if (!population.getPersons().containsKey(event.getPersonId())) return;
		vehicle2Driver.handleEvent(event);

		final PersonRecord record = records.computeIfAbsent(event.getPersonId(), PersonRecord::new);
		final double length = getLength(event.getLinkId());
		record.end(event.getTime(), length);
	}

	private double getLength(Id<Link> linkId) {
		return network.getLinks().get(linkId).getLength();
	}

	public class PersonRecord {
		private final Id<Person> id;
		private TDoubleList binStartTimes = new TDoubleArrayList();
		private TDoubleList distances = new TDoubleArrayList();

		private boolean onLink = false;
		private double currentStart = -1;
		private double enterLinkTime = -1;
		private double currentDistance = 0;

		private PersonRecord(Id<Person> id) {
			this.id = id;
		}

		private void start(double time) {
			if (onLink) throw new IllegalStateException();
			if (time >= currentStart + binSize) {
				 moveTo(((int) (time / binSize)) * binSize);
			}
			enterLinkTime = time;
			onLink = true;
		}

		private void moveTo(double time) {
			binStartTimes.add(currentStart);
			distances.add(currentDistance);
			currentStart = time;
			currentDistance = 0;
		}

		private void end(double time, double distance) {
			if (!onLink) throw new IllegalStateException();

			final double binEnd = currentStart + binSize;

			if (time < binEnd) {
				// in same time bin
				currentDistance += distance;
			}
			else {
				// changing time bin: need to do some magic there
				final double inBinFraction = (binEnd - enterLinkTime) / binSize;

				// add distance and record
				currentDistance += inBinFraction * distance;
				moveTo(binEnd);

				// move forward
				currentDistance = (1 - inBinFraction) * distance;
			}

			onLink = false;
		}

		public double calcTraveledDistance(double start, double end) {
			// TODO this should be relaxed or the interface changed
			if (end - start != binSize) throw new IllegalArgumentException();

			final int index = binStartTimes.binarySearch(start);

			return index >= 0 ? distances.get(index) : 0;
		}
	}
}
