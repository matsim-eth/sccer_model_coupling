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
	private final Network network;
	private final Map<Id<Person>,PersonRecord> records = new HashMap<>();

	public static class Module extends AbstractModule {
		@Override
		public void install() {
			addEventHandlerBinding().to(TravelDistanceEventHandler.class);
		}
	}

	@Inject
	public TravelDistanceEventHandler(Network network) {
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
		final PersonRecord record = records.computeIfAbsent(person, PersonRecord::new);
		record.start(event.getTime());
	}

	@Override
	public void handleEvent(LinkLeaveEvent event) {
		final Id<Person> person = vehicle2Driver.getDriverOfVehicle(event.getVehicleId());
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
		vehicle2Driver.handleEvent(event);

		final PersonRecord record = records.computeIfAbsent(event.getPersonId(), PersonRecord::new);
		record.start(event.getTime());
	}

	@Override
	public void handleEvent(VehicleLeavesTrafficEvent event) {
		vehicle2Driver.handleEvent(event);

		final PersonRecord record = records.computeIfAbsent(event.getPersonId(), PersonRecord::new);
		final double length = getLength(event.getLinkId());
		record.end(event.getTime(), length);
	}

	private double getLength(Id<Link> linkId) {
		return network.getLinks().get(linkId).getLength();
	}

	public static class PersonRecord {
		private final Id<Person> id;
		private TDoubleList enterTimes = new TDoubleArrayList();
		private TDoubleList exitTimes = new TDoubleArrayList();
		private TDoubleList distances = new TDoubleArrayList();
		private boolean onLink = false;

		private PersonRecord(Id<Person> id) {
			this.id = id;
		}

		private void start(double time) {
			if (onLink) throw new IllegalStateException();
			enterTimes.add(time);
			onLink = true;
		}

		private void end(double time, double distance) {
			if (!onLink) throw new IllegalStateException();
			exitTimes.add(time);
			distances.add(distance);
			onLink = false;
		}

		public double calcTraveledDistance(double start, double end) {
			final int startBinaryResult = enterTimes.binarySearch(start);
			final int endBinaryResult = exitTimes.binarySearch(end);

			final int startIndex = startBinaryResult >= 0 ? startBinaryResult : -startBinaryResult - 1;
			final int endIndex = endBinaryResult >= 0 ? endBinaryResult : -endBinaryResult - 1;

			// fraction of the first and last distance to consider: consider constant speed
			final double startFraction = (exitTimes.get(startIndex) - start) / (exitTimes.get(startIndex) - enterTimes.get(startIndex));
			final double endFraction = (end - enterTimes.get(endIndex)) / (exitTimes.get(endIndex) - enterTimes.get(endIndex));

			double distance = startFraction * distances.get(startIndex);

			for (int i=startIndex + 1; i < endIndex; i++) distance += distances.get(i);

			distance += endFraction * distances.get(endIndex);

			return distance;
		}
	}
}
