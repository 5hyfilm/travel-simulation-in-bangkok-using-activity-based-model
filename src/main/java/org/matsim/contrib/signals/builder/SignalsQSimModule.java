package org.matsim.contrib.signals.builder;

import org.matsim.core.mobsim.qsim.AbstractQSimModule;
import org.matsim.core.mobsim.qsim.qnetsimengine.QNetworkFactory;
import org.matsim.core.mobsim.qsim.qnetsimengine.QSignalsNetworkFactory;

/**
 * Custom override of the official SignalsQSimModule to match our monkey-patched SignalsModule.
 */
public class SignalsQSimModule extends AbstractQSimModule {
    public SignalsQSimModule() {
    }

    @Override
    protected void configureQSim() {
        bind(QNetworkFactory.class).to(QSignalsNetworkFactory.class);
    }
}
