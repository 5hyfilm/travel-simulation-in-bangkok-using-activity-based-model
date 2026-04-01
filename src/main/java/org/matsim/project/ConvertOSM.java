package org.matsim.project;

import org.matsim.api.core.v01.Id;
import org.matsim.api.core.v01.Scenario;
import org.matsim.api.core.v01.network.Network;
import org.matsim.api.core.v01.network.Node;
import org.matsim.api.core.v01.network.Link;
import org.matsim.core.config.ConfigUtils;
import org.matsim.core.config.Config;
import org.matsim.core.scenario.ScenarioUtils;
import org.matsim.core.utils.geometry.CoordinateTransformation;
import org.matsim.core.utils.geometry.transformations.TransformationFactory;
import org.matsim.core.network.NetworkUtils;
import org.matsim.core.utils.io.OsmNetworkReader;
import org.matsim.contrib.signals.data.SignalsData;
import org.matsim.contrib.signals.data.SignalsDataLoader;
import org.matsim.contrib.signals.data.SignalsScenarioWriter;
import org.matsim.contrib.signals.data.signalsystems.v20.*;
import org.matsim.contrib.signals.data.signalgroups.v20.*;
import org.matsim.contrib.signals.data.signalcontrol.v20.*;
import org.matsim.contrib.signals.SignalSystemsConfigGroup;
import org.matsim.contrib.signals.model.SignalSystem;
import org.matsim.contrib.signals.model.Signal;
import org.matsim.contrib.signals.model.SignalGroup;

import java.io.File;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Set;

public class ConvertOSM {
    private static final double CLUSTER_RADIUS_METERS = 80.0;
    private static final Set<String> MAIN_ROAD_TYPES = Set.of(
            "trunk",
            "primary"
    );

    public static void main(String[] args) {
        // 1) Config setup
        Config config = ConfigUtils.createConfig();
        SignalSystemsConfigGroup signalsConfig = ConfigUtils.addOrGetModule(config, SignalSystemsConfigGroup.GROUP_NAME, SignalSystemsConfigGroup.class);
        signalsConfig.setUseSignalSystems(true);

        // 2) Scenario setup
        Scenario scenario = ScenarioUtils.createScenario(config);
        Network network = scenario.getNetwork();
        SignalsData signalsData = new SignalsDataLoader(config).loadSignalsData();

        // 3) Coordinate transformation (UTM Zone 47N for Bangkok)
        CoordinateTransformation ct = TransformationFactory.getCoordinateTransformation(
                TransformationFactory.WGS84,
                "EPSG:32647"
        );

        String in = "preprocess/output/network.osm";
        String outDir = "data/processed";
        new File(outDir).mkdirs();

        // 4) Read OSM (Standard Reader - Fast)
        System.out.println("Step 1: Reading OSM Network (Fast Mode)...");
        OsmNetworkReader onr = new OsmNetworkReader(network, ct);
        // Only keep major roads to keep it sane for city-scale
        onr.setHighwayDefaults(1, "motorway",      1, 80.0/3.6, 1.2, 2000, true);
        onr.setHighwayDefaults(1, "motorway_link", 1, 60.0/3.6, 1.2, 1500, true);
        onr.setHighwayDefaults(2, "trunk",         1, 50.0/3.6, 1.2, 2000, false);
        onr.setHighwayDefaults(2, "trunk_link",    1, 50.0/3.6, 1.2, 1500, false);
        onr.setHighwayDefaults(3, "primary",       1, 40.0/3.6, 1.2, 1500, false);
        onr.setHighwayDefaults(3, "primary_link",  1, 40.0/3.6, 1.2, 1500, false);
        onr.setHighwayDefaults(4, "secondary",     1, 30.0/3.6, 1.2, 1000, false);
        onr.setHighwayDefaults(5, "tertiary",      1, 25.0/3.6, 1.2,  600, false);

        onr.parse(in);
        System.out.println("Network parsed. Nodes: " + network.getNodes().size() + ", Links: " + network.getLinks().size());

        // 5) Automated Signal Generation for clustered trunk/primary intersections
        System.out.println("Step 2: Generating Lämmer Signals for clustered trunk/primary intersections...");
        SignalSystemsData systems = signalsData.getSignalSystemsData();
        SignalGroupsData groups = signalsData.getSignalGroupsData();
        SignalControlData control = signalsData.getSignalControlData();

        List<IntersectionCandidate> candidates = collectIntersectionCandidates(network);
        System.out.println("Found " + candidates.size() + " intersection candidates before clustering.");

        List<List<IntersectionCandidate>> clusters = clusterCandidates(candidates, CLUSTER_RADIUS_METERS);
        System.out.println("Merged candidates into " + clusters.size() + " intersection clusters (radius " + CLUSTER_RADIUS_METERS + " m).");

        int systemCount = 0;
        for (List<IntersectionCandidate> cluster : clusters) {
            IntersectionCandidate anchor = chooseAnchorNode(cluster);
            Node node = anchor.node();
            Id<SignalSystem> systemId = Id.create(node.getId().toString(), SignalSystem.class);

            // 5.1) Create one system per clustered intersection, anchored at the strongest node
            SignalSystemData systemData = systems.getFactory().createSignalSystemData(systemId);
            systems.addSignalSystemData(systemData);

            // 5.2) Add Signals & Groups for each incoming link of the anchor node only
            int groupIdx = 1;
            for (Link link : node.getInLinks().values()) {
                Id<Signal> signalId = Id.create(link.getId().toString(), Signal.class);
                SignalData signalData = systems.getFactory().createSignalData(signalId);
                signalData.setLinkId(link.getId());
                systemData.addSignalData(signalData);

                Id<SignalGroup> groupId = Id.create(node.getId().toString() + "_" + groupIdx++, SignalGroup.class);
                SignalGroupData groupData = groups.getFactory().createSignalGroupData(systemId, groupId);
                groupData.addSignalId(signalId);
                groups.addSignalGroupData(groupData);
            }

            // 5.3) Set Lämmer Controller
            SignalSystemControllerData controllerData = control.getFactory().createSignalSystemControllerData(systemId);
            controllerData.setControllerIdentifier("LaemmerSignalController");
            control.addSignalSystemControllerData(controllerData);
            systemCount++;
        }

        System.out.println("Generated " + systemCount + " signal systems on clustered trunk/primary intersections.");

        // 6) Write output
        NetworkUtils.writeNetwork(network, outDir + "/network.xml.gz");
        SignalsScenarioWriter signalsWriter = new SignalsScenarioWriter();
        signalsWriter.setSignalSystemsOutputFilename(outDir + "/signalSystems.xml");
        signalsWriter.setSignalGroupsOutputFilename(outDir + "/signalGroups.xml");
        signalsWriter.setSignalControlOutputFilename(outDir + "/signalControl.xml");
        
        signalsWriter.writeSignalSystemsData(systems);
        signalsWriter.writeSignalGroupsData(groups);
        signalsWriter.writeSignalControlData(control);
        
        System.out.println("DONE! Files saved in " + outDir);
    }

    private static List<IntersectionCandidate> collectIntersectionCandidates(Network network) {
        List<IntersectionCandidate> candidates = new ArrayList<>();
        for (Node node : network.getNodes().values()) {
            IntersectionCandidate candidate = createIntersectionCandidate(node);
            if (candidate != null) {
                candidates.add(candidate);
            }
        }
        candidates.sort(Comparator.comparing(candidate -> candidate.node().getId().toString()));
        return candidates;
    }

    private static IntersectionCandidate createIntersectionCandidate(Node node) {
        int degree = node.getInLinks().size() + node.getOutLinks().size();
        if (node.getInLinks().isEmpty() || degree <= 3) {
            return null;
        }

        int mainRoadIncomingCount = countMainRoadIncoming(node);
        int mainRoadIncidentCount = countMainRoadIncident(node);
        if (mainRoadIncomingCount < 2 || mainRoadIncidentCount < 2) {
            return null;
        }

        return new IntersectionCandidate(node, mainRoadIncomingCount, mainRoadIncidentCount, degree);
    }

    private static List<List<IntersectionCandidate>> clusterCandidates(List<IntersectionCandidate> candidates, double radiusMeters) {
        List<List<IntersectionCandidate>> clusters = new ArrayList<>();
        boolean[] visited = new boolean[candidates.size()];

        for (int i = 0; i < candidates.size(); i++) {
            if (visited[i]) {
                continue;
            }

            List<IntersectionCandidate> cluster = new ArrayList<>();
            ArrayDeque<Integer> queue = new ArrayDeque<>();
            visited[i] = true;
            queue.add(i);

            while (!queue.isEmpty()) {
                int currentIndex = queue.removeFirst();
                IntersectionCandidate current = candidates.get(currentIndex);
                cluster.add(current);

                for (int j = 0; j < candidates.size(); j++) {
                    if (!visited[j] && isWithinRadius(current.node(), candidates.get(j).node(), radiusMeters)) {
                        visited[j] = true;
                        queue.add(j);
                    }
                }
            }

            clusters.add(cluster);
        }

        return clusters;
    }

    private static IntersectionCandidate chooseAnchorNode(List<IntersectionCandidate> cluster) {
        return cluster.stream()
                .max(Comparator
                        .comparingInt(IntersectionCandidate::mainRoadIncomingCount)
                        .thenComparingInt(IntersectionCandidate::degree)
                        .thenComparing(candidate -> candidate.node().getId().toString(), Comparator.reverseOrder()))
                .orElseThrow();
    }

    private static int countMainRoadIncoming(Node node) {
        int mainRoadIncomingCount = 0;
        for (Link link : node.getInLinks().values()) {
            if (isMainRoad(link)) {
                mainRoadIncomingCount++;
            }
        }
        return mainRoadIncomingCount;
    }

    private static int countMainRoadIncident(Node node) {
        int mainRoadIncidentCount = 0;
        for (Link link : node.getInLinks().values()) {
            if (isMainRoad(link)) {
                mainRoadIncidentCount++;
            }
        }
        for (Link link : node.getOutLinks().values()) {
            if (isMainRoad(link)) {
                mainRoadIncidentCount++;
            }
        }
        return mainRoadIncidentCount;
    }

    private static boolean isWithinRadius(Node a, Node b, double radiusMeters) {
        double dx = a.getCoord().getX() - b.getCoord().getX();
        double dy = a.getCoord().getY() - b.getCoord().getY();
        return dx * dx + dy * dy <= radiusMeters * radiusMeters;
    }

    private static boolean isMainRoad(Link link) {
        Object type = link.getAttributes().getAttribute("type");
        return type != null && MAIN_ROAD_TYPES.contains(type.toString());
    }

    private record IntersectionCandidate(Node node, int mainRoadIncomingCount, int mainRoadIncidentCount, int degree) {
    }
}
