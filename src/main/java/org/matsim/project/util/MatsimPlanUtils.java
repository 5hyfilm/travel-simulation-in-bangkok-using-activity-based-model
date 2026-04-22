package org.matsim.project.util;

import org.matsim.api.core.v01.TransportMode;
import org.matsim.api.core.v01.network.Link;
import org.matsim.api.core.v01.network.Network;
import org.matsim.api.core.v01.population.Activity;
import org.matsim.api.core.v01.population.PopulationFactory;
import org.matsim.core.network.NetworkUtils;
import org.matsim.facilities.ActivityFacility;

import java.util.*;

public class MatsimPlanUtils {

    /** Build an Activity with coord + facilityId + linkId + endTime (if >=0) */
    public static Activity activityAtFacility(PopulationFactory pf, ActivityFacility fac, String type,
                                              Network network, double endTimeIfNonNegative) {
        Activity act = pf.createActivityFromCoord(type, fac.getCoord());
        act.setFacilityId(fac.getId());
        Link link = nearestValidLink(fac, network);
        act.setLinkId(link.getId());
        if (endTimeIfNonNegative >= 0) {
            act.setEndTime(endTimeIfNonNegative);
        }
        return act;
    }

    /** Use facility's linkId if valid; else snap to nearest link. */
    public static Link nearestValidLink(ActivityFacility f, Network network) {
        var id = f.getLinkId();
        if (id != null && network.getLinks().containsKey(id)) {
            return network.getLinks().get(id);
        }
        return NetworkUtils.getNearestLink(network, f.getCoord());
    }

    /** Choose a facility option type from a preferred set; fall back to any available option. */
    public static String pickOneOptionType(ActivityFacility fac, Set<String> preferred) {
        var opts = fac.getActivityOptions().keySet();
        for (String p : preferred) if (opts.contains(p)) return p;
        return opts.iterator().next();
    }

    /** Random pick helper */
    public static <T> T pick(List<T> list, Random rnd) {
        return list.get(rnd.nextInt(list.size()));
    }

    /** Merge lists, skipping nulls */
    @SafeVarargs
    public static <T> List<T> merge(List<T>... lists) {
        List<T> out = new ArrayList<>();
        for (List<T> l : lists) if (l != null) out.addAll(l);
        return out;
    }

    /** Worklike types as in your data */
    public static final Set<String> WORKLIKE_TYPES =
            Set.of("commercial","school","university","health","public_service");

    /** Pick any facility from any worklike bucket (no zone constraint) */
    public static ActivityFacility pickAnyWorklike(Map<String, List<ActivityFacility>> byType, Random rnd) {
        List<ActivityFacility> merged = new ArrayList<>();
        for (String t : WORKLIKE_TYPES) {
            List<ActivityFacility> list = byType.getOrDefault(t, List.of());
            merged.addAll(list);
        }
        if (merged.isEmpty()) throw new RuntimeException("No worklike facilities found.");
        return merged.get(rnd.nextInt(merged.size()));
    }

    /** Pick any worklike facility but constrained by zone (fallback to any worklike if none in zone) */
    public static ActivityFacility pickAnyWorklikeInZone(Map<String, List<ActivityFacility>> byType,
                                                         FacilitySampler sampler,
                                                         Zone zone,
                                                         Random rnd) {
        List<ActivityFacility> filtered = new ArrayList<>();
        for (String t : WORKLIKE_TYPES) {
            for (ActivityFacility f : byType.getOrDefault(t, List.of())) {
                if (sampler.inZone(f.getCoord(), zone)) filtered.add(f);
            }
        }
        if (filtered.isEmpty()) {
            return pickAnyWorklike(byType, rnd);
        }
        return filtered.get(rnd.nextInt(filtered.size()));
    }
}
