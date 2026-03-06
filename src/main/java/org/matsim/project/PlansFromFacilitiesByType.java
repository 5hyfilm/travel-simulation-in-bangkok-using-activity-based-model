package org.matsim.project;

import org.matsim.api.core.v01.Id;
import org.matsim.api.core.v01.Scenario;
import org.matsim.api.core.v01.TransportMode;
import org.matsim.api.core.v01.network.Link;
import org.matsim.api.core.v01.population.*;
import org.matsim.core.config.Config;
import org.matsim.core.config.ConfigUtils;
import org.matsim.core.config.groups.ScoringConfigGroup;
import org.matsim.core.network.NetworkUtils;
import org.matsim.core.population.io.PopulationWriter;
import org.matsim.core.scenario.ScenarioUtils;
import org.matsim.facilities.ActivityFacilities;
import org.matsim.facilities.ActivityFacility;
import org.matsim.facilities.ActivityOption;

import java.util.*;
import java.util.stream.Collectors;

public class PlansFromFacilitiesByType {

    public static void main(String[] args) {
        String networkFile    = "data/processed/network_utm47.xml.gz";
        String facilitiesFile = "data/processed/facilities.xml.gz";
        String outPlans       = "data/processed/plans.fromFacilities.xml.gz";
        int nAgents           = 5000;

        // 1) Load
        Config config = ConfigUtils.createConfig();
        config.network().setInputFile(networkFile);
        config.facilities().setInputFile(facilitiesFile);
        Scenario scenario = ScenarioUtils.loadScenario(config);

        var network    = scenario.getNetwork();
        var facilities = scenario.getActivityFacilities();
        var population = scenario.getPopulation();
        var pf         = population.getFactory();

        // 2) Bucket facilities by their activity options
        Map<String, List<ActivityFacility>> byType = bucketFacilitiesByType(facilities);

        // Expected types in your data:
        // residential, commercial, park, school, university, health, public_service
        List<ActivityFacility> residential = byType.getOrDefault("residential", List.of());
        List<ActivityFacility> worklike = merge(
                byType.get("commercial"),
                byType.get("school"),
                byType.get("university"),
                byType.get("health"),
                byType.get("public_service")
        );
        List<ActivityFacility> parks = byType.getOrDefault("park", List.of());

        if (residential.isEmpty() || worklike.isEmpty()) {
            throw new RuntimeException("Need at least one residential and one worklike facility type.");
        }

        // 3) Add scoring params for every activity type we discovered
        addDefaultScoringForAllTypes(config, byType.keySet());

        // 4) Create plans using the facility’s type strings
        Random rnd = new Random(42);
        for (int i = 0; i < nAgents; i++) {
            Person person = pf.createPerson(Id.createPersonId("p" + i));
            Plan plan = pf.createPlan();

            ActivityFacility homeFac = pick(residential, rnd);
            ActivityFacility workFac = pick(worklike, rnd);

            // avoid identical facility for variety
            int guard = 0;
            while (workFac.getId().equals(homeFac.getId()) && guard++ < 10) {
                workFac = pick(worklike, rnd);
            }

            // optional leisure at a park for ~50% of agents
            boolean doLeisure = !parks.isEmpty() && rnd.nextBoolean();
            ActivityFacility parkFac = doLeisure ? pick(parks, rnd) : null;

            // times
            double depFromHome  = 7*3600 + rnd.nextInt(2*3600);   // 07:00–09:00
            double depFromWork  = 17*3600 + rnd.nextInt(2*3600);  // 17:00–19:00
            double depFromPark  = 19*3600 + rnd.nextInt(2*3600);  // 19:00–21:00 (if used)

            // HOME at residential
            plan.addActivity(activityAtFacility(pf, homeFac, "residential", network, depFromHome));

            // Leg to WORKLIKE
            plan.addLeg(pf.createLeg(TransportMode.car));

            // WORKLIKE (commercial/school/university/health/public_service)
            String workType = pickOneOptionType(workFac,
                    Set.of("commercial","school","university","health","public_service"));
            plan.addActivity(activityAtFacility(pf, workFac, workType, network, depFromWork));

            // Leg to optional LEISURE at park
            if (doLeisure) {
                plan.addLeg(pf.createLeg(TransportMode.car));
                plan.addActivity(activityAtFacility(pf, parkFac, "park", network, depFromPark));
            }

            // Leg back HOME
            plan.addLeg(pf.createLeg(TransportMode.car));

            // HOME again (open-ended)
            plan.addActivity(activityAtFacility(pf, homeFac, "residential", network, Double.NEGATIVE_INFINITY));

            person.addPlan(plan);
            person.setSelectedPlan(plan);
            population.addPerson(person);
        }

        // 5) Write
        new PopulationWriter(population).write(outPlans);
        System.out.println("Wrote: " + outPlans);
    }

    /** Build an Activity with coord + facilityId + linkId + endTime (if >=0) */
    private static Activity activityAtFacility(PopulationFactory pf, ActivityFacility fac, String type,
                                               org.matsim.api.core.v01.network.Network network,
                                               double endTimeIfNonNegative) {
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
    private static Link nearestValidLink(ActivityFacility f, org.matsim.api.core.v01.network.Network network) {
        var id = f.getLinkId();
        if (id != null && network.getLinks().containsKey(id)) {
            return network.getLinks().get(id);
        }
        return NetworkUtils.getNearestLink(network, f.getCoord());
    }

    /** Group facilities by each of their activity option types. */
    private static Map<String, List<ActivityFacility>> bucketFacilitiesByType(ActivityFacilities facilities) {
        Map<String, List<ActivityFacility>> map = new HashMap<>();
        for (ActivityFacility f : facilities.getFacilities().values()) {
            for (Map.Entry<String, ActivityOption> e : f.getActivityOptions().entrySet()) {
                String type = e.getKey();
                map.computeIfAbsent(type, k -> new ArrayList<>()).add(f);
            }
        }
        return map;
    }

    /** Random pick helper */
    private static <T> T pick(List<T> list, Random rnd) {
        return list.get(rnd.nextInt(list.size()));
    }

    /** Merge lists, skipping nulls */
    @SafeVarargs
    private static <T> List<T> merge(List<T>... lists) {
        List<T> out = new ArrayList<>();
        for (List<T> l : lists) if (l != null) out.addAll(l);
        return out;
    }

    /** Choose a facility option type from a preferred set; fall back to any available option. */
    private static String pickOneOptionType(ActivityFacility fac, Set<String> preferred) {
        var opts = fac.getActivityOptions().keySet();
        for (String p : preferred) if (opts.contains(p)) return p;
        return opts.iterator().next();
    }

    /** Add default scoring params for all discovered types (prevents missing-type errors). */
    private static void addDefaultScoringForAllTypes(Config config, Collection<String> types) {
        ScoringConfigGroup scoring = ConfigUtils.addOrGetModule(config, ScoringConfigGroup.class);

        Set<String> existing = scoring.getActivityParams().stream()
                .map(ScoringConfigGroup.ActivityParams::getActivityType)
                .collect(Collectors.toSet());

        for (String t : types) {
            if (!existing.contains(t)) {
                double typical;
                if ("residential".equals(t))      typical = 12 * 3600;
                else if ("park".equals(t))        typical =  2 * 3600;
                else                               typical =  8 * 3600; // worklike/other

                scoring.addActivityParams(
                        new ScoringConfigGroup.ActivityParams(t).setTypicalDuration(typical)
                );
            }
        }
    }
}
