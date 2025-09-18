package org.matsim.project;

import org.matsim.core.config.Config;
import org.matsim.core.config.ConfigUtils;
import org.matsim.core.controler.Controler;
import org.matsim.core.scenario.ScenarioUtils;
import org.matsim.contrib.otfvis.OTFVisLiveModule;

public class VisualizeBusRoute {
    public static void main(String[] args) {
        Config config = ConfigUtils.loadConfig("data/config.xml");
        var scenario = ScenarioUtils.loadScenario(config);
        Controler controler = new Controler(scenario);

        // เปิด OTFVis visualization
        controler.addOverridingModule(new OTFVisLiveModule());

        controler.run();
    }
}
