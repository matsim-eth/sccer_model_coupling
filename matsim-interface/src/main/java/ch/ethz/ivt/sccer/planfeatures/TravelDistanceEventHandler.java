package ch.ethz.ivt.sccer.planfeatures;

import com.google.inject.Inject;
import gnu.trove.list.TDoubleList;
import gnu.trove.list.array.TDoubleArrayList;
import org.matsim.api.core.v01.Id;
import org.matsim.api.core.v01.events.*;
import org.matsim.api.core.v01.events.handler.*;
import org.matsim.api.core.v01.network.Network;
import org.matsim.api.core.v01.population.Person;
import org.matsim.core.events.algorithms.Vehicle2DriverEventHandler;

/**
 * An event handler that stores traveled distance by car per time bin for each agent
 * @author thibautd
 */
public class TravelDistanceEventHandler implements
		LinkEnterEventHandler, LinkLeaveEventHandler,
		VehicleEntersTrafficEventHandler, VehicleLeavesTrafficEventHandler {
	private final Vehicle2DriverEventHandler vehicle2Driver = new Vehicle2DriverEventHandler();
	private final Network network;



	@Inject
	public TravelDistanceEventHandler(Network network) {
		this.network = network;
	}


	@Override
	public void handleEvent(LinkEnterEvent event) {
	}

	@Override
	public void handleEvent(LinkLeaveEvent event) {

	}

	@Override
	public void reset(int iteration) {
		vehicle2Driver.reset(iteration);
	}

	@Override
	public void handleEvent(VehicleEntersTrafficEvent event) {
		vehicle2Driver.handleEvent(event);


	}

	@Override
	public void handleEvent(VehicleLeavesTrafficEvent event) {
		vehicle2Driver.handleEvent(event);
	}

	public static class PersonRecord {
		private final Id<Person> id;
		private TDoubleList enterTimes = new TDoubleArrayList();
		private TDoubleList exitTimes = new TDoubleArrayList();
		private TDoubleList distances = new TDoubleArrayList();

		private PersonRecord(Id<Person> id) {
			this.id = id;
		}

		private void start(double time) {
			enterTimes.add(time);
		}

		private void end(double time, double distance) {
			exitTimes.add(time);
			distances.add(distance);
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
