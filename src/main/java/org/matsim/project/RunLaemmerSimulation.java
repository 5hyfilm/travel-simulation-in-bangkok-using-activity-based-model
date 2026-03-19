package org.matsim.project;

import com.google.inject.multibindings.MapBinder;
import org.matsim.api.core.v01.Scenario;
import org.matsim.core.config.Config;
import org.matsim.core.config.ConfigUtils;
import org.matsim.core.controler.AbstractModule;
import org.matsim.core.controler.Controler;
import org.matsim.core.scenario.ScenarioUtils;

import org.matsim.contrib.signals.SignalSystemsConfigGroup;
import org.matsim.contrib.signals.builder.Signals;
import org.matsim.contrib.signals.controller.SignalControllerFactory;
import org.matsim.contrib.signals.controller.laemmerFix.LaemmerConfigGroup;
import org.matsim.contrib.signals.controller.laemmerFix.LaemmerSignalController;

public class RunLaemmerSimulation {

    public static void main(String[] args) {
        // 1. Create default configuration
        Config config = ConfigUtils.createConfig();
        
        // 2. Setup Network and other basic simulation parameters
        config.network().setInputFile("data/processed/network.xml.gz");
        config.plans().setInputFile("data/processed/plan_20k.xml"); // <--- เอาพาทไฟล์ plan.xml ของคุณมาใส่ตรงนี้ครับ
        config.controller().setOutputDirectory("output/laemmer_simulation");
        config.controller().setLastIteration(1); // Set to 1 for quick testing

        // 3. Enable and setup Signals Configuration
        SignalSystemsConfigGroup signalsConfig = ConfigUtils.addOrGetModule(config, SignalSystemsConfigGroup.GROUP_NAME, SignalSystemsConfigGroup.class);
        signalsConfig.setUseSignalSystems(true);
        signalsConfig.setSignalSystemFile("data/processed/signalSystems.xml");
        signalsConfig.setSignalGroupsFile("data/processed/signalGroups.xml");
        signalsConfig.setSignalControlFile("data/processed/signalControl.xml");

        // 4. Add Laemmer Configuration
        LaemmerConfigGroup laemmerConfig = ConfigUtils.addOrGetModule(config, LaemmerConfigGroup.GROUP_NAME, LaemmerConfigGroup.class);


        // 5. Load Scenario
        Scenario scenario = ScenarioUtils.loadScenario(config);
        
        // 6. Initialize MATSim Controler
        Controler controler = new Controler(scenario);

        // 7. Configure Signals into Controler
        Signals.configure(controler);

        // 8. Inject Lämmer Custom Signal Controller via Guice MapBinder
        controler.addOverridingModule(new AbstractModule() {
            @Override
            public void install() {
                // This forces MATSim to use Laemmer for signals defined in signalControl.xml
                MapBinder<String, SignalControllerFactory> map = MapBinder.newMapBinder(binder(), String.class, SignalControllerFactory.class);
                map.addBinding(LaemmerSignalController.IDENTIFIER).to(LaemmerSignalController.LaemmerFactory.class);
            }
        });

        System.out.println("Simulation setup is complete! Running Lämmer Simulation...");
        
        controler.run(); 
    }
}
