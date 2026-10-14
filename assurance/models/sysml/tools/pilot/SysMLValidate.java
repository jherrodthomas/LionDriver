// Part of the LionDriver SysML model tooling (assurance/models/sysml/tools/pilot/validate.sh).
import java.nio.file.*;
import java.util.*;
import org.omg.sysml.interactive.*;
import org.eclipse.xtext.validation.Issue;

/** Parse and validate SysML v2 files in order with the OMG pilot implementation. Exit 1 on any error. */
public class SysMLValidate {
  public static void main(String[] args) throws Exception {
    SysMLInteractive s = SysMLInteractive.createInstance();
    s.loadLibrary(args[0]);
    int errors = 0, warnings = 0;
    for (int i = 1; i < args.length; i++) {
      String text = new String(Files.readAllBytes(Paths.get(args[i])));
      SysMLInteractiveResult r = s.process(text);
      List<Issue> issues = r.getIssues();
      for (Issue is : issues) {
        String sev = String.valueOf(is.getSeverity());
        if (sev.equals("ERROR")) errors++; else warnings++;
        System.out.println(args[i] + ":" + is.getLineNumber() + ":" + is.getColumn() + ": " + sev + ": " + is.getMessage());
      }
      System.out.println("checked " + args[i]);
    }
    System.out.println("errors=" + errors + " warnings=" + warnings);
    System.exit(errors > 0 ? 1 : 0);
  }
}
