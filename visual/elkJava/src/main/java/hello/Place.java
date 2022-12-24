package place;

// templage source:
// spring.io/guides/gs/maven/

// to build and run:
// mvn package
// java -jar target/gs-maven-0.1.0.jar

// see here for lists of elk stuff:
// https://oss.sonatype.org/content/repositories/snapshots/org/eclipse/elk/
// https://github.com/eclipse/elk/search?q=ELKGraphJSON


/* Sample json graph:
{
  id: "root",
  layoutOptions: { 'algorithm': 'layered' },
  children: [
    { id: "n1", width: 30, height: 30 },
    { id: "n2", width: 30, height: 30 },
    { id: "n3", width: 30, height: 30 }
  ],
  edges: [
    { id: "e1", sources: [ "n1" ], targets: [ "n2" ] },
    { id: "e2", sources: [ "n1" ], targets: [ "n3" ] }
  ]
} */

import org.joda.time.LocalTime;

import org.eclipse.elk.graph.*;
import org.eclipse.elk.graph.json.*;

import org.eclipse.elk.alg.layered.*;
import org.eclipse.elk.core.util.*;

import org.eclipse.elk.core.RecursiveGraphLayoutEngine;

import java.util.Scanner;
import java.io.File;
import java.io.FileWriter;
import java.io.IOException;


import java.lang.reflect.*;

public class Place {
	public static void main(String[] args) throws IOException {
		LocalTime currentTime = new LocalTime();
		System.out.println("The current local time is: " + currentTime);

		String inputJSON = "{\n  id: 'root',\n  layoutOptions: { 'algorithm': 'layered' },\n  children: [\n    { id: 'n1', width: 30, height: 30 },\n    { id: 'n2', width: 30, height: 30 },\n    { id: 'n3', width: 30, height: 30 }\n  ],\n  edges: [\n    { id: 'e1', sources: [ 'n1' ], targets: [ 'n2' ] },\n    { id: 'e2', sources: [ 'n1' ], targets: [ 'n3' ] }\n  ]\n}";

		// see https://devqa.io/java-read-files/
		String file = "src/file.txt";
		file = "./elkInput.txt";
		Scanner scanner = new Scanner(new File(file));
		scanner.useDelimiter("\\Z");
		// System.out.println(scanner.next());
		inputJSON = scanner.next();
		scanner.close();

		// see the end of https://www.eclipse.org/elk/documentation/tooldevelopers/graphdatastructure/jsonformat.html
		ElkNode root = ElkGraphJson.forGraph(inputJSON)
                           .toElk();

		// https://www.eclipse.org/forums/index.php/t/1095737/
		// see https://www.eclipse.org/elk/documentation/tooldevelopers/usingplainjavalayout.html
		// RecursiveGraphLayoutEngine is buggy ... perhaps see https://github.com/eclipse/sprotty-server/issues/82
		LayeredLayoutProvider layeredLayoutProvider = new LayeredLayoutProvider();
		RecursiveGraphLayoutEngine r = new RecursiveGraphLayoutEngine();
		BasicProgressMonitor progressMonitor = new BasicProgressMonitor();
		// layeredLayoutProvider.layout(root, progressMonitor);
		System.out.println(layeredLayoutProvider.getClass().getName());
		r.layout(root, progressMonitor);

		// System.out.println(root);
		// System.out.println(root.getClass().getDeclaredMethods());
		// Method[] m = root.getClass().getDeclaredMethods();
		// for(int i = 0; i < m.length; i++) {
		// 	System.out.println("method = " + m[i].toString());
		// }
		// System.out.println(root.getChildren().getParent());
		// m = root.getChildren().getClass().getDeclaredMethods();
		// for(int i = 0; i < m.length; i++) {
		// 	System.out.println("method = " + m[i].toString());
		// }
		// ElkNode c = root.getChildren(0);
		// System.out.println(c);

		// see the end of https://www.eclipse.org/elk/documentation/tooldevelopers/graphdatastructure/jsonformat.html
		String jsonOutput = ElkGraphJson.forGraph(root)
						// see options in https://github.com/eclipse/elk/blob/master/plugins/org.eclipse.elk.graph.json/src/org/eclipse/elk/graph/json/ElkGraphJson.java
                          .omitZeroPositions(false)
						  .omitZeroDimension(false)
                          .omitLayout(false)
                          .shortLayoutOptionKeys(false)
						  .omitUnknownLayoutOptions(false)
                          .prettyPrint(true)
                          .toJson();

		FileWriter myWriter = new FileWriter("./elkOutput.txt");
		myWriter.write(jsonOutput);
		myWriter.close();

		// System.out.println(jsonOutput);
		// System.out.println(jsonOutput.charAt(0));
		System.out.println("done");
	}
}
