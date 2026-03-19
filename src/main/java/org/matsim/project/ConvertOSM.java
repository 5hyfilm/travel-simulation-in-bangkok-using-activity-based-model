package org.matsim.project;

import org.matsim.api.core.v01.Scenario;
import org.matsim.api.core.v01.network.Network;
import org.matsim.core.config.ConfigUtils;
import org.matsim.core.config.Config;
import org.matsim.core.scenario.ScenarioUtils;
import org.matsim.core.utils.geometry.CoordinateTransformation;
import org.matsim.core.utils.geometry.transformations.TransformationFactory;
import org.matsim.core.network.NetworkUtils;
import org.matsim.contrib.signals.data.SignalsData;
import org.matsim.contrib.signals.data.SignalsDataLoader;
import org.matsim.contrib.signals.data.SignalsScenarioWriter;
import org.matsim.contrib.signals.network.SignalsAndLanesOsmNetworkReader;
import org.matsim.lanes.Lanes;
import org.matsim.contrib.signals.SignalSystemsConfigGroup;
import java.io.File;

public class ConvertOSM {
    public static void main(String[] args) {
        // 1) Config setup to enable Signals
        Config config = ConfigUtils.createConfig();
        SignalSystemsConfigGroup signalsConfig = ConfigUtils.addOrGetModule(config, SignalSystemsConfigGroup.GROUP_NAME, SignalSystemsConfigGroup.class);
        signalsConfig.setUseSignalSystems(true);

        // 2) Scenario & data structure setup
        Scenario scenario = ScenarioUtils.createScenario(config);
        Network network = scenario.getNetwork();
        Lanes lanes = scenario.getLanes();
        SignalsData signalsData = new SignalsDataLoader(config).loadSignalsData();

        // 3) Coordinate transform: keep WGS84 for now (safe & simple)
        CoordinateTransformation ct =
                TransformationFactory.getCoordinateTransformation(
                        TransformationFactory.WGS84,  // from OSM (WGS84)
                        TransformationFactory.WGS84   // to (identity)
                );

        // 4) Read OSM with the advanced reader that also extracts signals
        String in = "data/raw/pathumwan_M.osm";
        String outDir = "data/processed";
        new File(outDir).mkdirs();

        System.out.println("Reading OSM and extracting signals/lanes...");
        // Use the signal and lanes OSM reader
        SignalsAndLanesOsmNetworkReader onr = new SignalsAndLanesOsmNetworkReader(network, ct, signalsData, lanes);
        onr.setMergeOnewaySignalSystems(false); // Can help speed up a tiny bit
        
        onr.parse(in);

        // 5) Write extracted outputs
        NetworkUtils.writeNetwork(network, outDir + "/network.xml.gz");
        System.out.println("Wrote " + outDir + "/network.xml.gz");

        // Write Signals XML
        SignalsScenarioWriter signalsWriter = new SignalsScenarioWriter();
        signalsWriter.setSignalSystemsOutputFilename(outDir + "/signalSystems.xml");
        signalsWriter.setSignalGroupsOutputFilename(outDir + "/signalGroups.xml");
        signalsWriter.setSignalControlOutputFilename(outDir + "/signalControl.xml");
        
        signalsWriter.writeSignalSystemsData(signalsData.getSignalSystemsData());
        signalsWriter.writeSignalGroupsData(signalsData.getSignalGroupsData());
        signalsWriter.writeSignalControlData(signalsData.getSignalControlData());
        
        System.out.println("Wrote signals XML files in processed folder.");
    }
}
