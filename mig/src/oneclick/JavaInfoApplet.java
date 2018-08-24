
/* A simple applet to fetch information about the installed Java plugin */

import java.applet.*;
import java.awt.*;

public class JavaInfoApplet extends Applet { 
    private Label versionLabel; 
    
    public JavaInfoApplet() {
	versionLabel = new Label (" Java Version: " +
				  System.getProperty("java.version") +
				  " from " + System.getProperty("java.vendor"));
	this.add(versionLabel);
    }
}
