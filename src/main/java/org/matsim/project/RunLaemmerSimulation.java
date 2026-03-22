package org.matsim.project;

import com.google.inject.multibindings.MapBinder;
import org.matsim.api.core.v01.Scenario;
import org.matsim.api.core.v01.Id;
import org.matsim.api.core.v01.population.Person;
import org.matsim.api.core.v01.network.Network;
import org.matsim.core.config.Config;
import org.matsim.core.config.ConfigUtils;
import org.matsim.core.controler.AbstractModule;
import org.matsim.core.controler.Controler;
import org.matsim.core.scenario.ScenarioUtils;
import org.matsim.core.controler.OutputDirectoryHierarchy;
import org.matsim.core.config.groups.RoutingConfigGroup;

import org.matsim.contrib.signals.SignalSystemsConfigGroup;
import org.matsim.simwrapper.SimWrapperModule;
import org.matsim.contrib.signals.data.SignalsData;
import org.matsim.contrib.signals.data.SignalsDataLoader;
import org.matsim.contrib.signals.controller.SignalControllerFactory;
import org.matsim.contrib.signals.controller.laemmerFix.LaemmerConfigGroup;
import org.matsim.contrib.signals.controller.laemmerFix.LaemmerSignalController;
import org.matsim.contrib.signals.data.signalsystems.v20.SignalSystemData;
import org.matsim.contrib.signals.data.signalsystems.v20.SignalData;
import org.matsim.contrib.signals.data.signalgroups.v20.SignalGroupData;

import java.util.Properties;
import java.io.FileInputStream;
import java.io.IOException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Set;

public class RunLaemmerSimulation {

    public static void main(String[] args) {
        System.setProperty("matsim.qsim.usingFastCapacityUpdate", "false");

        Config config = ConfigUtils.createConfig();
        
        String baseDir = System.getProperty("user.dir") + "/";
        
        // Load dynamic settings from Python preprocessing
        int lastIteration = 0;
        int throttlingInterval = 5;
        try {
            Properties simProps = new Properties();
            simProps.load(new FileInputStream(baseDir + "preprocess/output/simulation.properties"));
            lastIteration = Integer.parseInt(simProps.getProperty("lastIteration", "0"));
            throttlingInterval = Integer.parseInt(simProps.getProperty("throttlingInterval", "5"));
            System.out.println("Loaded Simulation Settings: lastIteration=" + lastIteration + ", throttlingInterval=" + throttlingInterval);
        } catch (IOException | NumberFormatException e) {
            System.out.println("Could not load simulation.properties, using defaults (lastIteration=0, throttlingInterval=5)");
        }

        config.network().setInputFile(baseDir + "data/processed/network.cleaned.xml.gz");
        config.plans().setInputFile(baseDir + "preprocess/output/plan_20k.xml");
        config.controller().setOutputDirectory(baseDir + "output/laemmer_simulation");
        config.controller().setLastIteration(lastIteration); 
        ThrottledSignalEngine.updateInterval = throttlingInterval;

        config.controller().setOverwriteFileSetting(OutputDirectoryHierarchy.OverwriteFileSetting.overwriteExistingFiles);
        
        config.routing().setNetworkRouteConsistencyCheck(RoutingConfigGroup.NetworkRouteConsistencyCheck.disable);
        config.qsim().setTrafficDynamics(org.matsim.core.config.groups.QSimConfigGroup.TrafficDynamics.queue);
        config.qsim().setUsingFastCapacityUpdate(false);
        
        // Register activity types and set basic replanning to allow future iterations
        String[] activityTypes = {"home", "work", "education", "shopping", "leisure", "dining", "religion", "public_service", "other"};
        for (String actType : activityTypes) {
            org.matsim.core.config.groups.ScoringConfigGroup.ActivityParams params = new org.matsim.core.config.groups.ScoringConfigGroup.ActivityParams(actType);
            params.setTypicalDuration(3600.0);
            config.scoring().addActivityParams(params);
        }
        
        // Add a default replanning strategy to allow > 0 iterations without crashing
        org.matsim.core.config.groups.ReplanningConfigGroup.StrategySettings strategySettings = 
            new org.matsim.core.config.groups.ReplanningConfigGroup.StrategySettings();
        strategySettings.setStrategyName("ReRoute");
        strategySettings.setWeight(0.1);
        config.replanning().addStrategySettings(strategySettings);
        
        SignalSystemsConfigGroup signalsConfig = ConfigUtils.addOrGetModule(config, SignalSystemsConfigGroup.GROUP_NAME, SignalSystemsConfigGroup.class);
        signalsConfig.setUseSignalSystems(false); 
        signalsConfig.setSignalSystemFile(baseDir + "data/processed/signalSystems.xml");
        signalsConfig.setSignalGroupsFile(baseDir + "data/processed/signalGroups.xml");
        signalsConfig.setSignalControlFile(baseDir + "data/processed/signalControl.xml");

        @SuppressWarnings("unused")
        LaemmerConfigGroup laemmerConfig = ConfigUtils.addOrGetModule(config, LaemmerConfigGroup.GROUP_NAME, LaemmerConfigGroup.class);

        Scenario scenario = ScenarioUtils.loadScenario(config);
        System.out.println("DEBUG: Using full population of " + scenario.getPopulation().getPersons().size() + " people.");
        scenario.getConfig().qsim().setUsingFastCapacityUpdate(false);
        
        SignalsDataLoader loader = new SignalsDataLoader(scenario.getConfig());
        SignalsData signalsData = loader.loadSignalsData();
        cleanSignals(signalsData, scenario.getNetwork());
        scenario.addScenarioElement(SignalsData.ELEMENT_NAME, signalsData);
        
        Controler controler = new Controler(scenario);
        controler.addOverridingModule(new org.matsim.contrib.signals.builder.SignalsModule());
        controler.addOverridingQSimModule(new org.matsim.contrib.signals.builder.SignalsQSimModule());
        controler.addOverridingModule(new SimWrapperModule());
        
        controler.addOverridingModule(new AbstractModule() {
            @Override
            public void install() {
                MapBinder<String, SignalControllerFactory> map = MapBinder.newMapBinder(binder(), String.class, SignalControllerFactory.class);
                map.addBinding(LaemmerSignalController.IDENTIFIER).to(LaemmerSignalController.LaemmerFactory.class);
            }
        });

        System.out.println("Simulation setup complete! Running Lämmer Simulation with Simwrapper...");
        controler.run(); 
    }

    private static void cleanSignals(SignalsData signalsData, Network network) {
        if (signalsData == null) return;

        int removedSignalsCount = 0;
        int removedSystemsCount = 0;
        int removedGroupsCount = 0;
        
        Set<Id<org.matsim.contrib.signals.model.SignalSystem>> systemIdsToRemove = new HashSet<>();
        // Track which signal IDs were removed, per system (for cleaning up groups in surviving systems)
        Map<Id<org.matsim.contrib.signals.model.SignalSystem>, Set<Id<org.matsim.contrib.signals.model.Signal>>> removedSignalIdsBySystem = new HashMap<>();

        // Step 1: Remove signals referencing missing links; flag empty systems for removal
        if (signalsData.getSignalSystemsData() != null) {
            Map<Id<org.matsim.contrib.signals.model.SignalSystem>, SignalSystemData> systemDataMap = 
                signalsData.getSignalSystemsData().getSignalSystemData();
            
            Iterator<Map.Entry<Id<org.matsim.contrib.signals.model.SignalSystem>, SignalSystemData>> sysIter = 
                systemDataMap.entrySet().iterator();
            
            while (sysIter.hasNext()) {
                Map.Entry<Id<org.matsim.contrib.signals.model.SignalSystem>, SignalSystemData> sysEntry = sysIter.next();
                SignalSystemData system = sysEntry.getValue();
                Id<org.matsim.contrib.signals.model.SignalSystem> systemId = sysEntry.getKey();
                
                Map<Id<org.matsim.contrib.signals.model.Signal>, SignalData> signalDataMap = system.getSignalData();
                Iterator<Map.Entry<Id<org.matsim.contrib.signals.model.Signal>, SignalData>> signalIter = 
                    signalDataMap.entrySet().iterator();
                
                while (signalIter.hasNext()) {
                    Map.Entry<Id<org.matsim.contrib.signals.model.Signal>, SignalData> sigEntry = signalIter.next();
                    if (!network.getLinks().containsKey(sigEntry.getValue().getLinkId())) {
                        removedSignalIdsBySystem.computeIfAbsent(systemId, k -> new HashSet<>()).add(sigEntry.getKey());
                        signalIter.remove();
                        removedSignalsCount++;
                    }
                }
                
                if (signalDataMap.isEmpty()) {
                    systemIdsToRemove.add(systemId);
                    sysIter.remove();
                    removedSystemsCount++;
                }
            }
        }
        
        // Step 2: Clean signal groups
        // - Remove entire system's groups if system was removed
        // - For surviving systems: remove orphaned signal IDs from groups, then remove empty groups
        if (signalsData.getSignalGroupsData() != null) {
            Map<Id<org.matsim.contrib.signals.model.SignalSystem>, Map<Id<org.matsim.contrib.signals.model.SignalGroup>, SignalGroupData>> groupsBySystemId = 
                signalsData.getSignalGroupsData().getSignalGroupDataBySignalSystemId();
            
            Iterator<Map.Entry<Id<org.matsim.contrib.signals.model.SignalSystem>, Map<Id<org.matsim.contrib.signals.model.SignalGroup>, SignalGroupData>>> sysGroupIter = 
                groupsBySystemId.entrySet().iterator();
            
            while (sysGroupIter.hasNext()) {
                Map.Entry<Id<org.matsim.contrib.signals.model.SignalSystem>, Map<Id<org.matsim.contrib.signals.model.SignalGroup>, SignalGroupData>> entry = sysGroupIter.next();
                Id<org.matsim.contrib.signals.model.SignalSystem> sysId = entry.getKey();
                
                if (systemIdsToRemove.contains(sysId)) {
                    // Entire system was removed, drop all its groups
                    removedGroupsCount += entry.getValue().size();
                    sysGroupIter.remove();
                } else if (removedSignalIdsBySystem.containsKey(sysId)) {
                    // System survives but some of its signals were removed
                    Set<Id<org.matsim.contrib.signals.model.Signal>> removedSigIds = removedSignalIdsBySystem.get(sysId);
                    Iterator<Map.Entry<Id<org.matsim.contrib.signals.model.SignalGroup>, SignalGroupData>> groupIter = 
                        entry.getValue().entrySet().iterator();
                    while (groupIter.hasNext()) {
                        SignalGroupData group = groupIter.next().getValue();
                        // Remove references to deleted signals from this group
                        group.getSignalIds().removeAll(removedSigIds);
                        // If group is empty after cleaning, remove it too
                        if (group.getSignalIds().isEmpty()) {
                            groupIter.remove();
                            removedGroupsCount++;
                        }
                    }
                }
            }
        }
        
        // Step 3: Remove signal controllers for removed systems
        if (signalsData.getSignalControlData() != null) {
            Map<Id<org.matsim.contrib.signals.model.SignalSystem>, ?> controlMap = 
                signalsData.getSignalControlData().getSignalSystemControllerDataBySystemId();
            controlMap.keySet().removeAll(systemIdsToRemove);
        }
        
        System.out.println("DEBUG: Signal cleaning done — removed " + removedSignalsCount + " signals, " + removedSystemsCount + " systems, " + removedGroupsCount + " groups.");
    }
}
