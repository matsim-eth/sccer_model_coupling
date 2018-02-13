package ch.ethz.ivt.sccer.planfeatures;

import org.matsim.api.core.v01.population.Activity;
import org.matsim.api.core.v01.population.Leg;
import org.matsim.api.core.v01.population.Plan;
import org.matsim.core.router.TripStructureUtils;
import org.matsim.core.utils.misc.Time;

import java.util.ArrayList;
import java.util.List;

/**
 * @author thibautd
 */
public class Features {
	public static double longestStopTimeBetweenCarTrips( Plan plan ) {
		return getCarStops( plan ).stream()
				.mapToDouble( Stop::getDuration )
				.max()
				.orElse( -1 );
	}

	// different name in order to be able to use method references
	public static double longestStopTimeBetweenCarTripsInRange( Plan plan , double start_time_h , double end_time_h ) {
		return getCarStops( plan ).stream()
				.filter( s -> isInRange( s , start_time_h * 360 , end_time_h * 3600 ) )
				.mapToDouble( s -> durationInRange( s , start_time_h * 3600 , end_time_h * 3600 ) )
				.max()
				.orElse( -1 );
	}

	private static boolean isInRange( Stop stop , double start_s , double end_s ) {
		if ( stop.end < start_s ) return false;
		return !(stop.start > end_s);
	}

	private static double durationInRange( Stop stop , double start_s , double end_s ) {
		double stopStart = Math.max( start_s , stop.start );
		double stopEnd = Math.min( end_s , stop.end );
		return stopEnd - stopStart;
	}

	public static double longestCarTrip_m( Plan plan ) {
		return plan.getPlanElements().stream()
				.filter( pe -> pe instanceof Leg )
				.map( pe -> (Leg) pe )
				.filter( l -> l.getMode().equals( "car" ) )
				.mapToDouble( l -> l.getRoute().getDistance() )
				.max()
				.orElse( 0 );
	}

	public static double totalStopTimeBetweenCarTrips( Plan plan ) {
		return getCarStops( plan ).stream()
				.mapToDouble( Stop::getDuration )
				.sum();
	}

	private static List<Stop> getCarStops( Plan plan ) {
		Stop nightStop = new Stop();
		final List<Stop> stops = new ArrayList<>();

		Stop currentStop = nightStop;

		for ( Leg leg : TripStructureUtils.getLegs( plan ) ) {
			if ( !leg.getMode().equals( "car" ) ) continue;
			currentStop.end = leg.getDepartureTime();
			stops.add( currentStop );
			currentStop = new Stop();
			currentStop.start = leg.getDepartureTime() + leg.getTravelTime();
		}

		nightStop.start = currentStop.start - 24 * 3600;

		return stops;
	}

	public static double totalCarTraveledDistance_m( Plan plan ) {
		return plan.getPlanElements().stream()
				.filter( pe -> pe instanceof Leg )
				.map( pe -> (Leg) pe )
				.filter( l -> l.getMode().equals( "car" ) )
				.mapToDouble( l -> l.getRoute().getDistance() )
				.sum();
	}

	public static String isCarParkedInInterval( Plan plan , double start_s , double end_s ) {
		return ""+plan.getPlanElements().stream()
				.filter( pe -> pe instanceof Activity )
				.map( pe -> (Activity) pe )
				.anyMatch( a -> (a.getStartTime() == Time.UNDEFINED_TIME || a.getStartTime() < end_s) &&
						(a.getEndTime() == Time.UNDEFINED_TIME || a.getEndTime() > start_s ) );
	}

	private static class Stop {
		double start = Double.NaN;
		double end = Double.NaN;

		public double getDuration() {
			if ( Double.isNaN( start ) || Double.isNaN( end ) ) throw new IllegalStateException( "NaN times" );
			return end - start;
		}
	}
}
