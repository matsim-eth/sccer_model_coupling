package ch.ethz.ivt.sccer.analysis;

import org.matsim.core.api.experimental.events.EventsManager;
import org.matsim.core.events.EventsUtils;
import org.matsim.core.events.MatsimEventsReader;

import java.util.Collection;

public class TripReaderFromEvents {
	final private TripListener tripListener;

	public TripReaderFromEvents(TripListener tripListener) {
		this.tripListener = tripListener;
	}

	public Collection<TripItem> readTrips(String eventsPath) {
		EventsManager eventsManager = EventsUtils.createEventsManager();
		eventsManager.addHandler(tripListener);
		new MatsimEventsReader(eventsManager).readFile(eventsPath);
		return tripListener.getTripItems();
	}
}
