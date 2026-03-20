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

public class ConvertOSM {
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

        String in = "data/raw/pathumwan_M.osm";
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

        // 5) Automated Signal Generation for Junctions
        System.out.println("Step 2: Generating Lämmer Signals for Junctions...");
        SignalSystemsData systems = signalsData.getSignalSystemsData();
        SignalGroupsData groups = signalsData.getSignalGroupsData();
        SignalControlData control = signalsData.getSignalControlData();

        int systemCount = 0;
        for (Node node : network.getNodes().values()) {
            // Identify junctions: degree > 3 (at least 2 roads meeting)
            if (node.getInLinks().size() + node.getOutLinks().size() > 3 && !node.getInLinks().isEmpty()) {
                Id<SignalSystem> systemId = Id.create(node.getId().toString(), SignalSystem.class);
                
                // 5.1) Create System
                SignalSystemData systemData = systems.getFactory().createSignalSystemData(systemId);
                systems.addSignalSystemData(systemData);
                
                // 5.2) Add Signals & Groups for each incoming link
                int groupIdx = 1;
                for (Link link : node.getInLinks().values()) {
                    Id<Signal> signalId = Id.create(link.getId().toString(), Signal.class);
                    SignalData signalData = systems.getFactory().createSignalData(signalId);
                    signalData.setLinkId(link.getId());
                    systemData.addSignalData(signalData);
                    
                    // Group per incoming link (simplest for Lämmer to start with)
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
        }

        System.out.println("Generated " + systemCount + " signal systems.");

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
}

