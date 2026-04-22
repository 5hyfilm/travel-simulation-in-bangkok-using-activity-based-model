package org.matsim.project.util;

import org.matsim.api.core.v01.Coord;
import org.matsim.api.core.v01.network.Network;

public class BBox {
    public final double minX, maxX, minY, maxY;

    public BBox(double minX, double maxX, double minY, double maxY) {
        this.minX = minX; this.maxX = maxX; this.minY = minY; this.maxY = maxY;
    }

    public double w(){ return maxX - minX; }
    public double h(){ return maxY - minY; }

    public static BBox fromNetwork(Network network) {
        double minX = Double.POSITIVE_INFINITY, minY = Double.POSITIVE_INFINITY;
        double maxX = Double.NEGATIVE_INFINITY, maxY = Double.NEGATIVE_INFINITY;

        for (var n : network.getNodes().values()) {
            Coord c = n.getCoord();
            double x = c.getX(), y = c.getY();
            if (x < minX) minX = x; if (x > maxX) maxX = x;
            if (y < minY) minY = y; if (y > maxY) maxY = y;
        }
        return new BBox(minX, maxX, minY, maxY);
    }
}
