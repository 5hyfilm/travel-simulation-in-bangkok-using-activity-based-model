package org.matsim.project;

import org.matsim.api.core.v01.Coord;
import org.matsim.api.core.v01.Id;
import org.matsim.api.core.v01.Scenario;
import org.matsim.api.core.v01.network.Link;
import org.matsim.api.core.v01.network.Network;
import org.matsim.core.config.Config;
import org.matsim.core.config.ConfigUtils;
import org.matsim.core.network.NetworkUtils;
import org.matsim.core.population.routes.NetworkRoute;
import org.matsim.core.population.routes.RouteUtils;
import org.matsim.core.router.DijkstraFactory;
import org.matsim.core.router.costcalculators.OnlyTimeDependentTravelDisutility;
import org.matsim.core.router.util.LeastCostPathCalculator;
import org.matsim.core.router.util.TravelDisutility;
import org.matsim.core.router.util.TravelTime;
import org.matsim.core.scenario.ScenarioUtils;
import org.matsim.core.utils.geometry.transformations.TransformationFactory;
import org.matsim.pt.transitSchedule.api.*;

import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

public class GenerateTransitScheduleFromLatLonWithRoutes {
    public static void main(String[] args) {
        Path networkPath = Path.of("data/processed/network_clean_tuned.xml");
        Path scheduleOut = Path.of("data/processed/transitSchedule_line1.xml");

        // โหลด network
        Config config = ConfigUtils.createConfig();
        config.network().setInputFile(networkPath.toString());
        Scenario scenario = ScenarioUtils.loadScenario(config);
        Network network = scenario.getNetwork();

        TransitSchedule schedule = scenario.getTransitSchedule();
        TransitScheduleFactory fac = schedule.getFactory();

        // -----------------------------
        // ป้ายสาย 1 (lat, lon)
        // -----------------------------
        List<double[]> stopsLatLon = List.of(
                new double[]{13.7351511, 100.5318823}, // Sala Phra Kiew
                new double[]{13.7343487, 100.5333943}, // Political Science
                new double[]{13.7392848, 100.5347240}, // Patumwan Demonstration School
                new double[]{13.7417262, 100.5350965}, // Veterinary Science
                new double[]{13.7446968, 100.5355829}, // Chaloem Phao Junction
                new double[]{13.7458154, 100.5325744}, // Lido
                new double[]{13.7435144, 100.5304872}, // Pharmaceutical Science
                new double[]{13.7405426, 100.5300542}, // Triam Udom
                new double[]{13.7395576, 100.5308403}, // Architecture
                new double[]{13.7390833, 100.5331867}, // Arts
                new double[]{13.7375490, 100.5329169}, // Engineering
                new double[]{13.7351511, 100.5318823}  // Sala Phra Kiew (วนกลับ)
        );

        // -----------------------------
        // แปลง WGS84 → UTM47N
        // -----------------------------
        var ct = TransformationFactory.getCoordinateTransformation(
                TransformationFactory.WGS84, "EPSG:32647"
        );

        // -----------------------------
        // สร้าง TransitLine และ TransitRoute
        // -----------------------------
        TransitLine line = fac.createTransitLine(Id.create("CU_BUS_1", TransitLine.class));
        schedule.addTransitLine(line);

        List<TransitStopFacility> stopFacilities = new ArrayList<>();
        List<TransitRouteStop> routeStops = new ArrayList<>();

        int idx = 1;
        double t = 0.0;
        double dwell = 20.0;  // เวลาจอดที่ป้าย
        double hop   = 120.0; // เวลาวิ่งระหว่างป้าย

        for (double[] latlon : stopsLatLon) {
            Coord utm = ct.transform(new Coord(latlon[1], latlon[0])); // (lon,lat)
            Link nearest = NetworkUtils.getNearestLink(network, utm);

            TransitStopFacility stop = fac.createTransitStopFacility(
                    Id.create("stop" + idx, TransitStopFacility.class),
                    utm,
                    false
            );
            stop.setLinkId(nearest.getId());
            stop.setName("Stop" + idx);
            schedule.addStopFacility(stop);

            stopFacilities.add(stop);

            TransitRouteStop rs = fac.createTransitRouteStop(stop, t, t + dwell);
            routeStops.add(rs);

            t += dwell + hop;
            idx++;
        }

        // -----------------------------
        // TravelTime + Disutility สำหรับ Dijkstra
        // -----------------------------
        TravelTime travelTime = (link, time, person, vehicle) -> link.getLength() / link.getFreespeed();
        TravelDisutility travelDisutility = new OnlyTimeDependentTravelDisutility(travelTime);

        LeastCostPathCalculator router = new DijkstraFactory()
                .createPathCalculator(network, travelDisutility, travelTime);

        // -----------------------------
        // สร้าง NetworkRoute ระหว่างป้าย
        // -----------------------------
        List<Id<Link>> linkIds = new ArrayList<>();
        for (int i = 0; i < stopFacilities.size() - 1; i++) {
            Link fromLink = network.getLinks().get(stopFacilities.get(i).getLinkId());
            Link toLink   = network.getLinks().get(stopFacilities.get(i + 1).getLinkId());

            LeastCostPathCalculator.Path path = router.calcLeastCostPath(
                    fromLink.getToNode(), toLink.getFromNode(),
                    0, null, null
            );

            for (Link l : path.links) {
                linkIds.add(l.getId());
            }
        }

        Link firstLink = network.getLinks().get(stopFacilities.get(0).getLinkId());
        Link lastLink  = network.getLinks().get(stopFacilities.get(stopFacilities.size() - 1).getLinkId());

        NetworkRoute netRoute = RouteUtils.createLinkNetworkRouteImpl(firstLink.getId(), lastLink.getId());
        netRoute.setLinkIds(firstLink.getId(), linkIds, lastLink.getId());

        // -----------------------------
        // TransitRoute + Departure
        // -----------------------------
        TransitRoute route = fac.createTransitRoute(
                Id.create("route1", TransitRoute.class),
                netRoute,
                routeStops,
                "bus"
        );

        route.addDeparture(fac.createDeparture(Id.create("d1", Departure.class), 7 * 3600));

        line.addRoute(route);

        // -----------------------------
        // เขียนไฟล์
        // -----------------------------
        new org.matsim.pt.transitSchedule.api.TransitScheduleWriter(schedule)
                .writeFile(scheduleOut.toString());

        System.out.println("✅ transitSchedule_line1.xml generated (with NetworkRoute, MATSim 2025.0)");
    }
}
