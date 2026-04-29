/* *********************************************************************** *
 * project: org.matsim.*                                                   *
 * ...                                                                     *
 * *********************************************************************** */
package org.matsim.project;

import org.matsim.api.core.v01.Scenario;
import org.matsim.core.config.Config;
import org.matsim.core.config.ConfigUtils;
import org.matsim.core.controler.Controler;
import org.matsim.core.controler.OutputDirectoryHierarchy.OverwriteFileSetting;
import org.matsim.core.scenario.ScenarioUtils;

public class RunMatsim {

	public static void main(String[] args) {

		Config config;
		if (args == null || args.length == 0 || args[0] == null) {
			config = ConfigUtils.loadConfig("data/config.xml");
		} else {
			config = ConfigUtils.loadConfig(args[0]);
		}

		config.controller().setOverwriteFileSetting(OverwriteFileSetting.deleteDirectoryIfExists);

		// possibly modify config here

		// ---

		Scenario scenario = ScenarioUtils.loadScenario(config);
		new org.matsim.core.network.algorithms.NetworkCleaner().run(scenario.getNetwork());

		// possibly modify scenario here

		// ---

		Controler controler = new Controler(scenario);

		// possibly modify controler here

//      controler.addOverridingModule(new OTFVisLiveModule());
//      controler.addOverridingModule(new SimWrapperModule());

		// ---

		controler.run();
	}
}