package place;

// templage source:
// spring.io/guides/gs/maven/

// to build and run:
// mvn package
// java -jar target/gs-maven-0.1.0.jar

// see here for lists of elk stuff:
// https://oss.sonatype.org/content/repositories/snapshots/org/eclipse/elk/
// https://github.com/eclipse/elk/search?q=ELKGraphJSON

// ELK-related imports
import org.eclipse.elk.alg.layered.options.LayeredOptions;
import org.eclipse.elk.core.RecursiveGraphLayoutEngine;
import org.eclipse.elk.core.data.LayoutMetaDataService;
import org.eclipse.elk.core.util.BasicProgressMonitor;
import org.eclipse.elk.core.util.IElkProgressMonitor;
import org.eclipse.elk.graph.ElkNode;
import org.eclipse.elk.graph.json.ElkGraphJson;

import org.eclipse.elk.alg.layered.*;

// File IO-related imports
import java.util.Scanner;
import java.io.File;
import java.io.FileWriter;
import java.io.IOException;

public class Place {
	public static void main(String[] args) throws IOException {
		long heapMaxSize = Runtime.getRuntime().maxMemory();
		System.out.println("Heap max size: " + heapMaxSize);

		// see https://devqa.io/java-read-files/
		String file = "./elkInput.txt";
		Scanner scanner = new Scanner(new File(file));
		scanner.useDelimiter("\\Z");
		String inputJSON = scanner.next();
		scanner.close();

		// see the end of https://www.eclipse.org/elk/documentation/tooldevelopers/graphdatastructure/jsonformat.html
		ElkNode root = ElkGraphJson.forGraph(inputJSON)
                           .toElk();

		// see https://github.com/eclipse/elk/blob/master/test/org.eclipse.elk.shared.test/src/org/eclipse/elk/shared/test/PlainLayoutTest.java		   
        IElkProgressMonitor progressMonitor = new BasicProgressMonitor();
        // initialize the meta data service with ELK Layered's meta data
        LayoutMetaDataService service = LayoutMetaDataService.getInstance();
        service.registerLayoutMetaDataProviders(new LayeredOptions());
        // instantiate a recursive graph layout engine and execute layout
        RecursiveGraphLayoutEngine layoutEngine = new RecursiveGraphLayoutEngine();
        layoutEngine.layout(root, progressMonitor);

		// see the end of https://www.eclipse.org/elk/documentation/tooldevelopers/graphdatastructure/jsonformat.html
		String jsonOutput = ElkGraphJson.forGraph(root)
						// see options in https://github.com/eclipse/elk/blob/master/plugins/org.eclipse.elk.graph.json/src/org/eclipse/elk/graph/json/ElkGraphJson.java
                          .omitZeroPositions(false)
						  .omitZeroDimension(false)
                          .omitLayout(false)
                          .shortLayoutOptionKeys(true)
						  .omitUnknownLayoutOptions(false)
                          .prettyPrint(false)
                          .toJson();

		FileWriter myWriter = new FileWriter("./elkOutput.txt");
		myWriter.write(jsonOutput);
		myWriter.close();

		System.out.println("Finished running ELK");
	}
}
