package place;


import org.eclipse.elk.alg.layered.options.LayeredOptions;
// import org.eclipse.elk.alg.test.GraphTestUtils;
import org.eclipse.elk.core.RecursiveGraphLayoutEngine;
import org.eclipse.elk.core.data.LayoutMetaDataService;
import org.eclipse.elk.core.options.CoreOptions;
import org.eclipse.elk.core.util.BasicProgressMonitor;
import org.eclipse.elk.core.util.IElkProgressMonitor;
import org.eclipse.elk.graph.ElkNode;
// import org.junit.Test;

import com.google.common.collect.Iterators;
import com.google.common.collect.UnmodifiableIterator;


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
import org.eclipse.elk.alg.common.*;
import org.eclipse.elk.core.meta.*;

import java.util.Scanner;
import java.io.File;
import java.io.FileWriter;
import java.io.IOException;

import java.lang.reflect.*;

import com.google.common.collect.Iterators;
import com.google.common.collect.UnmodifiableIterator;
import org.eclipse.elk.core.options.*;
import org.eclipse.elk.alg.layered.options.*;



import org.eclipse.elk.alg.layered.options.LayeredOptions;
// import org.eclipse.elk.alg.test.GraphTestUtils;
import org.eclipse.elk.core.RecursiveGraphLayoutEngine;
import org.eclipse.elk.core.data.LayoutMetaDataService;
import org.eclipse.elk.core.options.CoreOptions;
import org.eclipse.elk.core.util.BasicProgressMonitor;
import org.eclipse.elk.core.util.IElkProgressMonitor;
import org.eclipse.elk.graph.ElkNode;
import com.google.common.collect.Iterators;
import com.google.common.collect.UnmodifiableIterator;

public class Place {
	public static void main(String[] args) throws IOException {
		LocalTime currentTime = new LocalTime();
		System.out.println("The current local time is: " + currentTime);
		long heapMaxSize = Runtime.getRuntime().maxMemory();
		System.out.println("Heap max size: " + heapMaxSize);

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

						   
		PlainLayoutTest p = new PlainLayoutTest();
		p.testPlainLayout(root);

		// see https://github.com/eclipse/elk/blob/3630e23fa5abc253233296e2bdf5e18828e5dba7/test/org.eclipse.elk.shared.test/src/org/eclipse/elk/shared/test/PlainLayoutTest.java
		// ((UnmodifiableIterator<ElkNode>)(Iterators.filter(root.eAllContents(), ElkNode.class))).forEachRemaining(node -> {
        //     if (!node.getChildren().isEmpty()) {
        //         node.setProperty(CoreOptions.ALGORITHM, LayeredOptions.ALGORITHM_ID);
        //     }
        // });
		root.setProperty(CoreOptions.ALGORITHM, LayeredOptions.ALGORITHM_ID);

		// // https://www.eclipse.org/forums/index.php/t/1095737/
		// // see https://www.eclipse.org/elk/documentation/tooldevelopers/usingplainjavalayout.html
		// // RecursiveGraphLayoutEngine is buggy ... perhaps see https://github.com/eclipse/sprotty-server/issues/82
		// // LayeredLayoutProvider layeredLayoutProvider = new LayeredLayoutProvider();
		// RecursiveGraphLayoutEngine r = new RecursiveGraphLayoutEngine();
		// BasicProgressMonitor progressMonitor = new BasicProgressMonitor();
		// // layeredLayoutProvider.initialize(null);
		// // layeredLayoutProvider.layout(root, progressMonitor);
		// // System.out.println(layeredLayoutProvider.getClass().getName());
		// r.layout(root, progressMonitor);

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
                        //   .prettyPrint(true)
                          .prettyPrint(false)
                          .toJson();

		FileWriter myWriter = new FileWriter("./elkOutput.txt");
		myWriter.write(jsonOutput);
		myWriter.close();

		// System.out.println(jsonOutput);
		// System.out.println(jsonOutput.charAt(0));
		System.out.println("done");

		// System.out.println("starting");
		// PlainLayoutTest p = new PlainLayoutTest();
		// p.testPlainLayout();
		// System.out.println("done");
	}
}

// see https://github.com/eclipse/elk/blob/master/test/org.eclipse.elk.shared.test/src/org/eclipse/elk/shared/test/PlainLayoutTest.java
// slightly modified to take an input graph
/**
 * Test and demonstration of 'Plain Java Layout'. 
 */
class PlainLayoutTest {

    /**
     * Test a plain Java layout on a hierarchical graph using the ELK Layered algorithm.
     */
    // @Test
    public void testPlainLayout(ElkNode parentNode) {
        // create a hierarchical KGraph for layout
        // ElkNode parentNode = GraphTestUtils.createHierarchicalGraph();

		// String inputJSON = "{\n  id: 'root',\n  layoutOptions: { 'algorithm': 'layered' },\n  children: [\n    { id: 'n1', width: 30, height: 30 },\n    { id: 'n2', width: 30, height: 30 },\n    { id: 'n3', width: 30, height: 30 }\n  ],\n  edges: [\n    { id: 'e1', sources: [ 'n1' ], targets: [ 'n2' ] },\n    { id: 'e2', sources: [ 'n1' ], targets: [ 'n3' ] }\n  ]\n}";
		// ElkNode parentNode = ElkGraphJson.forGraph(inputJSON)
		// 						.toElk();

        // configure every hierarchical node to use ELK Layered (which would also be the default) 
        // getAllElkNodes(parentNode).forEachRemaining(node -> {
        //     if (!node.getChildren().isEmpty()) {
        //         node.setProperty(CoreOptions.ALGORITHM, LayeredOptions.ALGORITHM_ID);
        //     }
        // });

        // create a progress monitor
        IElkProgressMonitor progressMonitor = new BasicProgressMonitor();

        // initialize the meta data service with ELK Layered's meta data
        LayoutMetaDataService service = LayoutMetaDataService.getInstance();
        service.registerLayoutMetaDataProviders(new LayeredOptions());

        // instantiate a recursive graph layout engine and execute layout
        RecursiveGraphLayoutEngine layoutEngine = new RecursiveGraphLayoutEngine();
        layoutEngine.layout(parentNode, progressMonitor);

        // output layout information
        printLayoutInfo(parentNode, progressMonitor);
    }

    /**
     * Outputs layout information on the console.
     * 
     * @param parentNode
     *            parent node representing a graph
     * @param progressMonitor
     *            progress monitor for the layout run
     */
    private void printLayoutInfo(final ElkNode parentNode, final IElkProgressMonitor progressMonitor) {
        // print execution time of the algorithm run
        // SUPPRESS CHECKSTYLE NEXT MagicNumber
        System.out.println("Execution time: " + progressMonitor.getExecutionTime() * 1000 + " ms");

        // print position of each node
        // getAllElkNodes(parentNode).forEachRemaining(node -> {
        //     System.out.println(node.getLabels().get(0).getText() + ": x = " + node.getX() + ", y = "
        //             + node.getY());
        // });
    }
    
    private UnmodifiableIterator<ElkNode> getAllElkNodes(final ElkNode parentNode) {
        return Iterators.filter(parentNode.eAllContents(), ElkNode.class);
    }
}