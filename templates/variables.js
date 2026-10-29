// figma-offline-kit: read this file's local variables with the Figma Plugin API.
// Run it through Figma's MCP server (use_figma) on the design-system file, save the JSON it returns to a file,
// then: python kit.py tokens import <file> <saved.json>
// The result has the same shape as Figma's REST endpoint GET /v1/files/:key/variables/local.
const collections = await figma.variables.getLocalVariableCollectionsAsync();
const variables = {};
const variableCollections = {};
for (const c of collections) {
  variableCollections[c.id] = {
    id: c.id, name: c.name, key: c.key, modes: c.modes, defaultModeId: c.defaultModeId,
    variableIds: c.variableIds, hiddenFromPublishing: c.hiddenFromPublishing, remote: c.remote,
  };
  for (const id of c.variableIds) {
    const v = await figma.variables.getVariableByIdAsync(id);
    if (!v) continue;
    variables[id] = {
      id: v.id, name: v.name, key: v.key, variableCollectionId: v.variableCollectionId,
      resolvedType: v.resolvedType, valuesByMode: v.valuesByMode, scopes: v.scopes,
      codeSyntax: v.codeSyntax, description: v.description,
      hiddenFromPublishing: v.hiddenFromPublishing, remote: v.remote,
    };
  }
}
return JSON.stringify({ meta: { variables, variableCollections } });
